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
	geneUrl: 'gene/get/' + dataset_id,
	termUrl: 'term/get/' + dataset_id,
	libUrl: 'library/get/' + dataset_id
}

sdvConfig = $.extend(sdvDefaultConfig, sdvConfig)

var sdv = new Scatter3dView(sdvConfig)

var legend = new Legend({scatterPlot: sdv, h: window.innerHeight + 'px', container: container})

var controler = new Controler({scatterPlot: sdv, h: window.innerHeight + 'px', w: '200px', container: container})


var geneSearchSelectize = new SearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'gene/query/' + dataset_id 
})

var termSearchSelectize = new TermSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'term/query/' + dataset_id,
	optGroupUrl: 'library/query/' + dataset_id
})

var libSearchSelectize = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'library/query/' + dataset_id,
	label: 'Predict cell type and tissue:',
	options: [{name: 'ARCHS4_Tissues'}, {name: 'ARCHS4_Cell-lines'}]
})

var libSearchSelectize2 = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'library/query/' + dataset_id,
	label: 'Predict pathways and upstream regulators:',
	options: [{name: 'ChEA_2016'}, {name: 'KEA_2015'}, {name: 'KEGG_2016'}]
})

// DOMs for brush selection
var brushController = new BrushController({scatterPlot: sdv, container: "#controls"})
var brushModalBtn = new BrushBtns({scatterPlot: sdv, container: container, base_url: 'brush/'+dataset_id})
var brushModal = new BrushModal({scatterPlot: sdv});

brushController.listenTo(brushModalBtn, 'clearBrush', brushController.depress)

var overlay = new Overlay({scatterPlot: sdv})
