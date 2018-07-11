var textures = new Textures()

var sd = new ScatterData({
	url : 'graph/' + dataset_id + '/' + graph_name   // need to get this variable from server
})

var container = document.getElementById("body")
var width = container.clientWidth;
var height = container.clientHeight;

var sdvDefaultConfig = {
	container: container,
	WIDTH: width,
	HEIGHT: height,	
	model: sd,
	textures: textures,
	pointSize: 12,
	is3d: false,
}

sdvConfig = $.extend(sdvDefaultConfig, sdvConfig)

var sdv = new Scatter3dView(sdvConfig)

var legend = new Legend({scatterPlot: sdv, h: window.innerHeight + 'px', container: container})

var controler = new Controler({scatterPlot: sdv, h: window.innerHeight + 'px', w: '200px', container: container})

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

// search probabilities for single predicted labels
// var labelSearchSelectize = new TermSearchSelectize({
// 	scatterPlot: sdv, 
// 	container: "#controls", 
// 	synonymsUrl: 'label/query/' + dataset_id,
// 	optGroupUrl: 'prediction/query/' + dataset_id,
// 	retrieveUrl: 'label/get/' + dataset_id
// })

// search top enriched terms
var libSearchSelectize = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'library/query/' + dataset_id,
	retrieveUrl: 'library/get/' + dataset_id,
	label: 'Enriched cell type and tissue:',
	optionsShow: ['ARCHS4_Tissues', 'ARCHS4_Cell-lines']
})

var libSearchSelectize2 = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'library/query/' + dataset_id,
	retrieveUrl: 'library/get/' + dataset_id,
	label: 'Predict pathways and upstream regulators:',
	optionsShow: ['ChEA_2016', 'KEA_2015', 'KEGG_2016']
})

// search top predicted labels
var predSearchSelectize = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'prediction/query/' + dataset_id,
	retrieveUrl: 'prediction/get/' + dataset_id,
	label: 'Predicted cell types from expression vectors:',
	optionsShow: ['human_cell_type', 'mouse_cell_type']
})


// DOMs for brush selection
var brushController = new BrushController({scatterPlot: sdv, container: "#controls"})
var brushModalBtn = new BrushBtns({scatterPlot: sdv, container: container, base_url: 'brush/'+dataset_id})
var brushModal = new BrushModal({scatterPlot: sdv});

brushController.listenTo(brushModalBtn, 'clearBrush', brushController.depress)

var overlay = new Overlay({scatterPlot: sdv})
