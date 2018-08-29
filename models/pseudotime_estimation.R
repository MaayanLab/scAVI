python_home <- "~/.virtualenvs/r-reticulate/bin/python"
reticulate::use_python(python_home)

library(dplyr)
library(monocle)
library(tibble)


# Make a CellDataSet object
# @expr_df: CPM expression data.frame (genes by samples) 
makeCellData <- function(expr_df) {
	genes <- rownames(expr_df)
	expr_mat = data.matrix(expr_df)
	num_cells_expressed <- (expr_mat > 0.1) + 0
	num_cells_expressed <- Matrix::rowSums(num_cells_expressed)
	fd <- data.frame(num_cells_expressed=num_cells_expressed, row.names = genes)
	fd <- new("AnnotatedDataFrame", data = fd)
	pd <- new("AnnotatedDataFrame", data = data.frame(row.names=colnames(expr_mat)))
	
	newCellDataSet(expr_mat,
		phenoData = pd,
		featureData = fd,
		lowerDetectionLimit = 0.1,
		expressionFamily = tobit(0.1))
}

makeCellData3 <- function(expr_df) {
	genes <- rownames(expr_df)
	expr_mat = data.matrix(expr_df)
	num_cells_expressed <- (expr_mat > 0.1) + 0
	num_cells_expressed <- Matrix::rowSums(num_cells_expressed)
	fd <- data.frame(num_cells_expressed=num_cells_expressed, row.names = genes)
	fd <- new("AnnotatedDataFrame", data = fd)
	pd <- data.frame(row.names=colnames(expr_mat))
	# a hack to avoid error when running `partitionCells`
	pd['foo'] = 'bar'
	pd <- new("AnnotatedDataFrame", data = pd)
	
	newCellDataSet(expr_mat,
		phenoData = pd,
		featureData = fd,
		lowerDetectionLimit = 0.1)
}

# Run the entire Monocle-DDRTree pipeline to 
# 1) clustering
# 2) identify DEGs across clusters
# 3) ordering cells/psudotime estimation
runMonocleDDRTree <- function(cds) {
	# tSNE and clustering cells
	cds <- reduceDimension(cds, 
		max_components = 2,
		norm_method = 'log',
		reduction_method = 'tSNE',
		verbose = T)
	cds <- clusterCells(cds, verbose = T)
	n_clusters <- length(unique(cds$Cluster))
	if (n_clusters > 1){
		# get DEGs among clusters
		cds_expressed_genes <-  row.names(subset(fData(cds), num_cells_expressed >= 10))
		clustering_DEG_genes <- differentialGeneTest(cds[cds_expressed_genes,], 
			fullModelFormulaStr = '~Cluster',
			cores = 8)
		# order cells with top 1000 DEGs
		cds_ordering_genes <- row.names(clustering_DEG_genes)[order(clustering_DEG_genes$qval)][1:1000]

	} else { # only 1 cluster
		RowVar <- function(x, ...) {
			# from https://stackoverflow.com/questions/25099825/row-wise-variance-of-a-matrix-in-r
			rowSums((x - rowMeans(x, ...))^2, ...)/(dim(x)[2] - 1)
		}
		# use genes with high variances for ordering cell
		gene_variances <- RowVar(exprs(cds))
		cds_ordering_genes <- names(gene_variances[order(gene_variances, decreasing = T)])[1:1000]
	}
	cds <- setOrderingFilter(cds, ordering_genes = cds_ordering_genes)
	cds <- reduceDimension(cds, method = 'DDRTree', norm_method = 'log')
	cds <- orderCells(cds)
	return(cds)
}


runMonocleUMAPsimplePPT <- function(cds) {
	# 1. Noramlize and pre-process the data
	cds <- estimateSizeFactors(cds)
	cds <- preprocessCDS(cds, 
		num_dim = 50,
		norm_method = 'log',
		method = 'PCA'
		)
	# 2. Reduce the dimensionality of the data
	cds <- reduceDimension(cds, max_components = 3,
	                       reduction_method = 'UMAP',
	                       metric="cosine",
	                       verbose = F)
	# 3. Partition the cells into supergroups
	cds <- partitionCells(cds)
	# 4. Learn the principal graph
	cds <- learnGraph(cds,
	                  max_components = 3,
	                  RGE_method = 'SimplePPT',
	                  partition_component = T,
	                  verbose = F)
	## Not Implemented: Monocle 3 doesn't seem to support ordering by 
	# the expression of a list of genes. Will need know how to automatically
	# find the root cell instead.

	# # 5. order cells
	# cds <- orderCells(cds, 
	# 	root_pr_nodes = get_correct_root_state(cds,
	#                                            cell_phenotype = 'cell_type2',
	#                                            "Multipotent progenitors"))
	return(cds)
}

# Convert cds object to edge_df and data_df for making plot
# @ref: https://github.com/cole-trapnell-lab/monocle-release/blob/ea83577c511564222bd08a35a9f944b07ccd1a42/R/plotting.R#L53
convertToDataFrames <- function(cds) {
	sample_name <- NA
	sample_state <- pData(cds)$State
	# data_dim_1 <- NA
	# data_dim_2 <- NA
	theta <- 0
	x <- 1
	y <- 2

	lib_info_with_pseudo <- pData(cds)

	reduced_dim_coords <- reducedDimK(cds)

	ica_space_df <- Matrix::t(reduced_dim_coords) %>%
	  as.data.frame() %>%
	  select_(prin_graph_dim_1 = x, prin_graph_dim_2 = y) %>%
	  mutate(sample_name = rownames(.), sample_state = rownames(.))

	dp_mst <- minSpanningTree(cds)

	edge_df <- dp_mst %>%
	  igraph::as_data_frame() %>%
	  select_(source = "from", target = "to") %>%
	  left_join(ica_space_df %>% select_(source="sample_name", source_prin_graph_dim_1="prin_graph_dim_1", source_prin_graph_dim_2="prin_graph_dim_2"), by = "source") %>%
	  left_join(ica_space_df %>% select_(target="sample_name", target_prin_graph_dim_1="prin_graph_dim_1", target_prin_graph_dim_2="prin_graph_dim_2"), by = "target")

	data_df <- t(monocle::reducedDimS(cds)) %>%
	  as.data.frame() %>%
	  select_(x = x, y = y) %>%
	  rownames_to_column("sample_name") %>%
	  mutate(sample_state) %>%
	  left_join(lib_info_with_pseudo %>% rownames_to_column("sample_name"), by = "sample_name")

	return_rotation_mat <- function(theta) {
	  theta <- theta / 180 * pi
	  matrix(c(cos(theta), sin(theta), -sin(theta), cos(theta)), nrow = 2)
	}
	rot_mat <- return_rotation_mat(theta)

	cn1 <- c("x", "y")
	cn2 <- c("source_prin_graph_dim_1", "source_prin_graph_dim_2")
	cn3 <- c("target_prin_graph_dim_1", "target_prin_graph_dim_2")
	data_df[, cn1] <- as.matrix(data_df[, cn1]) %*% t(rot_mat)
	edge_df[, cn2] <- as.matrix(edge_df[, cn2]) %*% t(rot_mat)
	edge_df[, cn3] <- as.matrix(edge_df[, cn3]) %*% t(rot_mat)
	# Drop the redundant sample_state column
	data_df[,"sample_state"] = NULL
	return(list(edge_df=edge_df, data_df=data_df))
}


convertToDataFrames3 <- function(cds) {
	sample_name <- NA
	sample_state <- pData(cds)$louvain_component

	x <- 1
	y <- 2
	z <- 3

	lib_info_with_pseudo <- pData(cds)

	reduced_dim_coords <- reducedDimK(cds)

	ica_space_df <- Matrix::t(reduced_dim_coords) %>%
	  as.data.frame() %>%
	  select_(prin_graph_dim_1 = x, prin_graph_dim_2 = y, prin_graph_dim_3 = z) %>%
	  mutate(sample_name = rownames(.), sample_state = rownames(.))

	dp_mst <- minSpanningTree(cds)

	edge_df <- dp_mst %>%
	  igraph::as_data_frame() %>%
	  select_(source = "from", target = "to") %>%
	  left_join(ica_space_df %>% select_(source="sample_name", source_prin_graph_dim_1="prin_graph_dim_1", 
	  	source_prin_graph_dim_2="prin_graph_dim_2", 
	  	source_prin_graph_dim_3="prin_graph_dim_3"), by = "source") %>%
	  left_join(ica_space_df %>% select_(target="sample_name", target_prin_graph_dim_1="prin_graph_dim_1", 
	  	target_prin_graph_dim_2="prin_graph_dim_2", 
	  	target_prin_graph_dim_3="prin_graph_dim_3"), by = "target")

	data_df <- t(monocle::reducedDimS(cds)) %>%
	  as.data.frame() %>%
	  select_(x = x, y = y, z = z) %>%
	  rownames_to_column("sample_name") %>%
	  mutate(sample_state) %>%
	  left_join(lib_info_with_pseudo %>% rownames_to_column("sample_name"), by = "sample_name")

	# Drop the redundant sample_state column
	data_df[,"sample_state"] = NULL
	return(list(edge_df=edge_df, data_df=data_df))
}

#  Run the entire Monocle pipeline
runMonoclePipeline <- function(expr_df) {
	cds <- makeCellData(expr_df)
	cds <- runMonocleDDRTree(cds)
	convertToDataFrames(cds)	
}

runMonocle3Pipeline <- function(expr_df){
	cds <- makeCellData3(expr_df)
	cds <- runMonocleUMAPsimplePPT(cds)
	convertToDataFrames3(cds)
}
