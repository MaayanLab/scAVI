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
	geneUrl: 'gene'
}

sdvConfig = $.extend(sdvDefaultConfig, sdvConfig)

var sdv = new Scatter3dView(sdvConfig)

var legend = new Legend({scatterPlot: sdv, h: window.innerHeight, container: container})

var controler = new Controler({scatterPlot: sdv, h: window.innerHeight, w: 200, container: container})


var geneSearchSelectize = new SearchSelectize({
	scatterPlot: sdv, 
	container: "#controls", 
	synonymsUrl: 'query_genes'
})

// var sigSimSearch = new SigSimSearchForm({
// 	scatterPlot: sdv, 
// 	container: "#controls",
// 	action: 'search/' + graph_name
// })

var overlay = new Overlay({scatterPlot: sdv})
