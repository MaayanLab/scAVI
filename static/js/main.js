var textures = new Textures()

var sd = new ScatterData({
	url : 'graph/' + graph_name // need to get this variable from server
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
	geneUrl: 'gene/get',
	termUrl: 'term/get',
	libUrl: 'library/get'
}

sdvConfig = $.extend(sdvDefaultConfig, sdvConfig)

var sdv = new Scatter3dView(sdvConfig)

var legend = new Legend({scatterPlot: sdv, h: window.innerHeight + 'px', container: container})

var controler = new Controler({scatterPlot: sdv, h: window.innerHeight + 'px', w: '200px', container: container})

// seletize(s) for searching single genes, pathways, gene-set libraries
var geneSearchSelectize = new SearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'gene/query'
})

var termSearchSelectize = new TermSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'term/query',
	optGroupUrl: 'library/query'
})

var libSearchSelectize = new LibSearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'library/query'
})

// DOMs for brush selection
var brushController = new BrushController({scatterPlot: sdv, container: "#controls"})
var brushModalBtn = new BrushBtns({scatterPlot: sdv, container: container})
var brushModal = new BrushModal({scatterPlot: sdv});

brushController.listenTo(brushModalBtn, 'clearBrush', brushController.depress)

var overlay = new Overlay({scatterPlot: sdv})
