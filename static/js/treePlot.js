/*
The models and views for minimal spanning tree.
*/

var TreeData = Backbone.Model.extend({
	// base model for the tree 
	defaults: {
		data: null, // an array of objects
		url: 'tree',
	},

	url: function(){
		return this.attributes.url;
	},

	parse: function(response){
		// called whenever a model's data is returned by the server
		this.n = response.length;
		this.positions = [];
		for (var i = response.length - 1; i >= 0; i--) {
			var edge = response[i];
			var x = edge['source_prin_graph_dim_1'],
				y = edge['source_prin_graph_dim_2'],
				z = edge['source_prin_graph_dim_3'] || 0,
				xend = edge['target_prin_graph_dim_1'],
				yend = edge['target_prin_graph_dim_2'],
				zend = edge['target_prin_graph_dim_3'] || 0;
			var points = new Float32Array([x, y, z, xend, yend, zend]);
			this.positions.push(points)
		}
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		// fetch json data from server
		// this.fetch();
	},

});

var TreeView = Backbone.View.extend({
	model: TreeData,
	
	defaults: {
		color: 0x0000ff,
		scene: null,
		sdv: null,
	},
	
	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		var self = this;
		var sdv = this.sdv;

		$.when(this.model.fetch(), sdv.model.fetch()).done(function(){
			self.render();
		});
	},

	setUpObject: function(){
		var model = this.model;
		this.parentObject = new THREE.Object3D();

		for (var i = model.positions.length - 1; i >= 0; i--) {
			var position = model.positions[i];
			var lineGeometry = new THREE.BufferGeometry();
			lineGeometry.addAttribute( 'position', new THREE.BufferAttribute( position, 3) );
			var object = new THREE.Line( lineGeometry, new THREE.LineBasicMaterial({color: new THREE.Color(this.color)}) );
			this.parentObject.add(object)
		}
	},

	render: function(){
		this.setUpObject()
		this.sdv.scene.add(this.parentObject)
		this.sdv.renderScatter()
	},

	removeObject: function(){
		// remove object from scene and this view if exists
		if (this.parentObject){
			var scene = this.sdv.scene;
			scene.remove(scene.getObjectById(this.parentObject.id));					
		}
		this.parentObject = undefined;
	},

	changeModel: function(url){
		// change model and update the visualization
		this.model = new TreeData({url: url})
		this.removeObject()
		this.listenTo(this.model, 'sync', this.render)
		
		var graph_name = url.split('/').slice(2, 3)[0];
		if (graph_name === 'monocle'){
			this.model.fetch()
		}
	},

});
