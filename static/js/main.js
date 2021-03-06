var textures = new Textures()

var n_dim = sdvConfig.is3d ? 3 : 2;

var sd = new ScatterData({
	url : 'graph/' + dataset_id + '/' + graph_name + '/' + n_dim  // need to get this variable from server
})

var container = document.getElementById("body")
var width = container.clientWidth;
var height = container.clientHeight;

if (mobilecheck() || width < 420){ // small or mobile screen
	height = Math.min(width, height)
	width = height
}

var sdvDefaultConfig = {
	container: container,
	WIDTH: width,
	HEIGHT: height,	
	model: sd,
	textures: textures,
	// pointSize: 12, // 2d
	// is3d: false,

	// pointSize: 0.5, // 3d
	// is3d: true,
}

sdvConfig = $.extend(sdvDefaultConfig, sdvConfig)

var sdv = new Scatter3dView(sdvConfig)

// Create Tree model and view regardless if there is a tree in the visualization 
var td = new TreeData({
	url: 'tree/' + dataset_id + '/' + graph_name + '/' + n_dim
})

var tdv = new TreeView({
	model: td,
	sdv: sdv
})
tdv.listenTo(sdv, 'modelChanged', function(url){
	var treeUrl = url.replace('graph', 'tree')
	this.changeModel(treeUrl)
})

var inferredMeta = ['DBSCAN-clustering', 'KMeans-clustering',
	'Cluster', 'Pseudotime', 'delta', 'rho',
	'Size_Factor'
];

if (mobilecheck() || width < 420){ // small or mobile screen
	// make wrapper for controls
	$('body>div:eq(1)').after($('<div>').attr('class', 'container')
		.attr('id', 'controler-container'))

	var legend = new Legend({scatterPlot: sdv, 
		h: window.innerHeight/3 + 'px', 
		container: container
	})
	
	var controler = new Controler({scatterPlot: sdv, 
		h: window.innerHeight/3 + 'px', 
		w: window.innerWidth * 0.9 + 'px', 
		container: document.getElementById('controler-container'),
		inferredMeta: inferredMeta,
	})
} else {
	var legend = new Legend({scatterPlot: sdv, 
		h: window.innerHeight + 'px', 
		container: container})
	var controler = new Controler({scatterPlot: sdv, 
		h: window.innerHeight * 0.67 + 'px', 
		w: '200px', 
		container: container,
		inferredMeta: inferredMeta,
	})
}

// search expression of single genes
var geneSearchSelectize = new SearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'gene/query/' + dataset_id,
	retrieveUrl: 'gene/get/' + dataset_id 
})

// search enrichment scores of single terms
var termSearchSelectize = new TermSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'term/query/' + dataset_id,
	optGroupUrl: 'library/query/' + dataset_id,
	retrieveUrl: 'term/get/' + dataset_id
})

// search top enriched terms
var libSearchSelectize = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'library/query/' + dataset_id,
	retrieveUrl: 'library/get/' + dataset_id,
	label: 'Enrichment analysis:',
	optionsShow: ['ARCHS4_Tissues', 'ARCHS4_Cell-lines',
		'ChEA_2016', 'KEA_2015', 'KEGG_2016', 
		'MGI_Mammalian_Phenotype_2017', 'GO_Biological_Process_2018'
	]
})

// var libSearchSelectize2 = new LibSearchSelectize({
// 	scatterPlot: sdv, 
// 	container: "#controls", 
// 	synonymsUrl: 'library/query/' + dataset_id,
// 	retrieveUrl: 'library/get/' + dataset_id,
// 	label: 'Predict pathways and upstream regulators:',
// 	optionsShow: ['ChEA_2016', 'KEA_2015', 'KEGG_2016', 
// 		'MGI_Mammalian_Phenotype_2017', 'GO_Biological_Process_2018']
// })

// search top predicted labels
// var predSearchSelectize = new LibSearchSelectize({
// 	scatterPlot: sdv, 
// 	container: "#controls", 
// 	synonymsUrl: 'prediction/query/' + dataset_id,
// 	retrieveUrl: 'prediction/get/' + dataset_id,
// 	label: 'Predicted cell types from expression vectors:',
// 	optionsShow: []
// })

// DOMs for brush selection
var brushController = new BrushController({scatterPlot: sdv, container: "#controls"})
var brushModalBtn = new BrushBtns({scatterPlot: sdv, container: container, base_url: 'brush/'+dataset_id})
var brushModal = new BrushModal({scatterPlot: sdv});

brushController.listenTo(brushModalBtn, 'clearBrush', brushController.depress)	

var dimToggle = new DimToggle({scatterPlot: sdv, 
	container: "#dim-toggle", 
	graphs: graphs,
	defaultColorKey: sdvDefaultConfig.colorKey
})
var visBtnGroup = new VisualizationBtnGroup({scatterPlot: sdv, 
	container: "#vis-btn-group", 
	graphs: graphs,
	defaultColorKey: sdvDefaultConfig.colorKey
})

var overlay = new Overlay({scatterPlot: sdv})
// respond to sdv.change events 
overlay.listenTo(sdv, 'modelChanging', function(url){
	this.render()
	this.changeMessage('Switching visualization...')
})
overlay.listenTo(sdv, 'modelChanged', function(url){
	this.remove()
})
