/*
The models and views for the scatter plot.
*/

function isInt(n){
    return Number(n) === n && n % 1 === 0;
}

function getType(n){
	var type = typeof n;
	if (type === 'number'){
		if (isInt(n)){
			type = 'int';
		} else {
			type = 'float'
		}
	}
	return type;
}

function getArrayType(arr){
	// get the data type of items in an array
	// skipping the null(s)
	var arr = _.filter(arr, function(x){ return x !== null})
	var dtypes = new Set(_.map(arr, getType))
	var dtype = [...dtypes][0];
	if (dtypes.size > 1){
		if (dtypes.has('float')){ // mixture of floats, ints, or strings
			dtype = 'float'
		}
	}
	return dtype;
}

function arrayHasNull(arr){
	// assert if null in an array
	var s = new Set(arr)
	return s.has(null);
}

/** 
 * convenience for converting JSON color to rgba that canvas wants
 * Be nice to handle different forms (e.g. no alpha, CSS style, etc.)
 */ 
function getCanvasColor(color){
	return "rgba(" + color.r + "," + color.g + "," + color.b + "," + color.a + ")"; 
}

RARE = 'other'

function encodeRareCategories(arr, k){
	// Count occurences of each unique categories in arr, 
	// then keep top k and encode rare categories as 'rares'
	var counts = _.countBy(arr);
	// sort values
	var counts = _.sortBy(_.pairs(counts), function(tuple){ return -tuple[1]; });
	// get top k frequent categories
	var frequentCategories = _.map(counts.slice(0, k), function(tuple){ return tuple[0]; });
	for (var i = 0; i < arr.length; i++) {
		if (frequentCategories.indexOf(arr[i]) === -1){
			arr[i] = RARE;
		}
	};
	return arr;
}

function binValues(arr, nbins){
	// Binning continues array of values in to nbins
	var extent = d3.extent(arr);
	var min = parseFloat(extent[0]);
	var max = parseFloat(extent[1]);
	var interval = (max - min)/nbins; // bin width

	var domain = _.range(1, nbins).map(function(i){ return i*interval+min;}); // bin edges
	var labels = [min.toFixed(2)+ ' to '+domain[0].toFixed(2)];

	for (var i = 0; i < nbins-1; i++) {
		if (i === nbins-2){ // the last bin
			var label = domain[i].toFixed(2) + ' to ' + max.toFixed(2);
		} else{
			var label = domain[i].toFixed(2) + ' to ' + domain[i+1].toFixed(2);
		}
		labels.push(label);
	};
	return {labels: labels, domain: domain, min: min, max: max, interval:interval};
}

function binValues2(arr, domain){
	// Binning continues array of values by a given binEdges (domain)
	// domain: [0.001, 0.01, 0.05, 0.1, 1] 
	// domain should include the largest (rightest) value
	var extent = d3.extent(arr);
	var min = parseFloat(extent[0]);
	var max = parseFloat(extent[1]);

	var labels = ['0 to ' + domain[0]];
	var nbins = domain.length;
	
	for (var i = 0; i < nbins-1; i++) {
		var label = domain[i] + ' to ' + domain[i+1];
		labels.push(label);
	};
	return {labels: labels, domain: domain.slice(0,-1), min: min, max: max};
}

function binBy(list, key, nbins){
	// similar to _.groupBy but applying to continues values using `binValues`
	// list: an array of objects
	// key: name of the continues variable
	// nbins: number of bins
	var values = _.pluck(list, key);
	var binnedValues = binValues(values, nbins);
	var labels = binnedValues.labels;
	var min = binnedValues.min;
	var interval = binnedValues.interval;

	var grouped = _.groupBy(list, function(obj){
		var i = Math.floor((obj[key] - min)/interval);
		if (i === nbins) { // the max value
			i = nbins - 1;
		}
		return labels[i];
	});
	return grouped;
}

function binBy2(list, key, domain){
	// wrapper for `binValuesBy`
	var values = _.pluck(list, key);
	var binnedValues = binValues2(values, domain);
	var labels = binnedValues.labels;

	var grouped = _.groupBy(list, function(obj){
		var i = _.filter(domain, function(edge){ return edge < obj[key];}).length;
		return labels[i];
	});
	return grouped;
}


var _ScatterDataSubset = Backbone.Model.extend({
	defaults: {
		data: null, // an array of objects
	},
	// base model for data points 
	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.n = this.data.length;

		// generate arrays of positions
		this.indices = new Uint32Array( this.n );
		this.positions = new Float32Array( this.n * 3 );

		for (var i = 0; i < this.data.length; i++) {
			this.indices[i] = i; 
			this.positions[ i*3 ] = this.data[i].x;
			this.positions[ i*3+1 ] = this.data[i].y;
			this.positions[ i*3+2 ] = this.data[i].z || 0;
		};
	},

	getAttr: function(metaKey){
		// return an array of attributes 
		return _.map(this.data, function(record){ return record[metaKey]; });
	},

	getLabels: function(labelKeys){
		// return an array of label texts given a list of labelKeys
		var labels = new Array( this.n );
		for (var i = 0; i < this.data.length; i++) {
			var record = this.data[i];
			var label = '';
			for (var j = 0; j < labelKeys.length; j++) {
				var labelKey = labelKeys[j];
				if (labelKey === 'Time'){
					label += labelKey + ': ' + record[labelKey] + ' hours\n';
				} else if (labelKey === 'Dose'){
					label += labelKey + ': ' + record[labelKey] + ' μM\n';
				} else {
					label += labelKey + ': ' + record[labelKey] + '\n';
				}
			};
			labels[i] = label
		};
		return labels;
	}

});


var Scatter3dCloud = Backbone.View.extend({
	// this is the view for points of a single shape
	model: _ScatterDataSubset,

	defaults: {
		texture: null, // the THREE.Texture instance
		data: null, // expect data to be an array of objects
		labelKey: ['sig_id'],
		pointSize: 0.01,
		sizeAttenuation: true, // true for 3d, false for 2d
		opacity: 0.6, // opacity of the points
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		//
		this.setUpScatterGeometry();
	},

	setUpScatterGeometry: function(){
		var model = this.model;

		this.geometry = new THREE.BufferGeometry();
		this.geometry.setIndex( new THREE.BufferAttribute( model.indices, 1 ) );
		this.geometry.addAttribute( 'position', new THREE.BufferAttribute( model.positions, 3 ) );		
		this.geometry.addAttribute( 'label', new THREE.BufferAttribute( model.getLabels(this.labelKey), 1 ) );
		this.geometry.addAttribute( 'id', new THREE.BufferAttribute( model.getAttr('sample_id'), 1))

	    this.geometry.computeBoundingSphere();

	    var texture = this.texture;
	    if (texture){
			var material = new THREE.PointsMaterial({ 
				vertexColors: THREE.VertexColors,
				size: this.pointSize, 
				sizeAttenuation: this.sizeAttenuation, 
				map: texture, 
				alphaTest: 0.2, 
				transparent: true,
				opacity: this.opacity
				});
	    } else{
			var material = new THREE.PointsMaterial({
				vertexColors: THREE.VertexColors,
				size: 0.1,
				sizeAttenuation: this.sizeAttenuation, 
				alphaTest: 0.2, 
				opacity: this.opacity,
				transparent: true,
			});
	    }
		this.points = new THREE.Points( this.geometry, material );
	},

	setColors: function(colorScale, metaKey){
		// Color points by a certain metaKey given colorScale
		var metas = this.model.getAttr(metaKey)
		// construct colors BufferAttribute
		var colors = new Float32Array( this.model.n * 3);
		if (colorScale.hasOwnProperty('domain')){
			var frequentCategories = colorScale.domain().slice();	
		}else{
			var frequentCategories = {length: 2};
		}
		
		if (frequentCategories.length > 3){
			for (var i = metas.length - 1; i >= 0; i--) {
				if (frequentCategories.indexOf(metas[i]) === -1){
					var color = colorScale(RARE);
				} else {
					var color = colorScale(metas[i]);
				}
				color = new THREE.Color(color);
				color.toArray(colors, i*3)
			};
		} else {
			for (var i = metas.length - 1; i >= 0; i--) {
				var color = colorScale(metas[i]);
				color = new THREE.Color(color);
				color.toArray(colors, i*3)
			};			
		}

		this.geometry.addAttribute( 'color', new THREE.BufferAttribute( colors.slice(), 3 ) );
		// this.geometry.attributes.color.needsUpdate = true;
	},

	setSingleColor: function(color){
		var color = new THREE.Color(color);
		var colors = new Float32Array( this.model.n * 3 );

		for (var i = this.model.n; i >= 0; i--) {
			color.toArray(colors, i*3);
		};
		this.geometry.addAttribute( 'color', new THREE.BufferAttribute( colors.slice(), 3 ));
	},

	intersectBox: function(extent){
		var positions = this.geometry.getAttribute('position');
		var intersectingIdx = [];

		for (var i = 0, len = positions.count; i < len; i++) {
			var x = positions.array[i*3],
				y = positions.array[i*3 + 1];
			if (extent[0][0] <= x && x < extent[1][0] 
				&& extent[0][1] <= y && y < extent[1][1]){
				intersectingIdx.push(i)
			}
		}
		return intersectingIdx;
	},

	highlightIntersectedPoints: function(intersectingIdx){
		var geometry = this.geometry;

		geometry.attributes.color.needsUpdate = true;

		for (var i = 0; i < intersectingIdx.length; i++) {
			var idx = intersectingIdx[i]
			geometry.attributes.color.array[idx*3] = 0.1;
			geometry.attributes.color.array[idx*3+1] = 0.8;
			geometry.attributes.color.array[idx*3+2] = 0.1;
		
		}
	}

});

var ScatterData = Backbone.Model.extend({
	// model for the data (positions) and metadata. 
	defaults: {
		url: 'toy',
		n: 100, // Number of data points to retrieve, or number of data points retrieved
		metas: [], // store information about meta [{name: 'metaKey', nUnique: nUnique, type: type}]
		data: [], // store data
	},

	url: function(){
		return this.attributes.url;
	},

	parse: function(response){
		// called whenever a model's data is returned by the server
		this.n = response.length;
		var xyz = ['x', 'y', 'z'];
		for (var key in response[0]){
			if (xyz.indexOf(key) === -1){ 
				var arr = _.pluck(response, key)
				var nUnique = _.unique(arr).length;
				var type = getArrayType(arr)
				var hasNull = arrayHasNull(arr)
				this.metas.push({
					name: key,
					nUnique: nUnique,
					type: type,
					hasNull: hasNull
				});
			}
		}
		this.data = response;
	},

	initialize: function(options){
		// called on construction
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		// empty metas slot on initialize
		this.metas = [];
		// fetch json data from server
		// this.fetch();
	},

	groupBy: function(metaKey){
		// group by a metaKey and return an object of _ScatterDataSubset objects keyed by metaKey
		var dataSubsets = _.groupBy(this.data, metaKey);
		var scatterDataSubsets = _.mapObject(dataSubsets, function(records, key){
			return new _ScatterDataSubset({data: records});
		});
		return scatterDataSubsets;
	},

	binBy: function(metaKey, nbins){
		var dataSubsets = binBy(this.data, metaKey, nbins);
		var scatterDataSubsets = _.mapObject(dataSubsets, function(records, key){
			return new _ScatterDataSubset({data: records});
		});
		return scatterDataSubsets;
	},

	binBy2: function(metaKey, domain){
		var dataSubsets = binBy2(this.data, metaKey, domain);
		var scatterDataSubsets = _.mapObject(dataSubsets, function(records, key){
			return new _ScatterDataSubset({data: records});
		});
		return scatterDataSubsets;
	},

	getAttr: function(metaKey){
		// return an array of attributes 
		return _.map(this.data, function(record){ return record[metaKey]; });
	},

	setAttr: function(key, values){
		for (var i = 0; i < this.data.length; i++) {
			var rec = this.data[i];
			rec[key] = values[i];
			this.data[i] = rec;
		};
		// add meta data of this new attr
		this.metas.push({
			name: key,
			nUnique: _.unique(values).length,
			type: getArrayType(values),
			hasNull: arrayHasNull(values)
		});
	},
});


var Scatter3dView = Backbone.View.extend({
	// this is the view for all points
	model: ScatterData,

	defaults: {
		WIDTH: window.innerWidth,
		HEIGHT: window.innerHeight,
		DPR: window.devicePixelRatio,
		container: document.body,
		labelKey: ['sig_id'], // which metaKey to use as labels
		colorKey: 'dose', // which metaKey to use as colors
		shapeKey: null,
		clouds: [], // to store Scatter3dCloud objects
		textures: null, // the Textures collection instance
		pointSize: 0.01, // the size of the points
		showStats: false, // whether to show Stats
		is3d: true, // 3d or 2d
		raycasterThreshold: undefined, // raycaster.Points.threshold
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		var self = this;
		this.listenToOnce(this.textures, 'allLoaded', function(){

			self.listenTo(self.model, 'sync', function(){
				self.setUpStage();
				// self.colorBy(self.colorKey);
				self.shapeBy(self.shapeKey);
				if(self.is3d){
					self.animate();
				}

			});
		});
	},

	setUpStage: function(){
		// set up THREE.js visualization components
		this.aspectRatio = this.WIDTH / this.HEIGHT;
		
		// set up scene, renderer
		this.scene = new THREE.Scene();
		// this.scene.fog = new THREE.FogExp2( 0xcccccc, 0.002 );

		this.renderer = new THREE.WebGLRenderer({
			// canvas: document.getElementById('renderer'),
			alpha: true, antialias: true});
		// this.renderer.setClearColor( this.scene.fog.color );
		// this.renderer.setClearColor( 0xcccccc );
		this.renderer.setClearColor( 0xffffff );
		// Do not set DPR for now: https://github.com/mrdoob/three.js/issues/2833
		// devices with DPR > 1 may experience poorer canvas qualities
		// this.renderer.setPixelRatio( this.DPR );
		this.renderer.setSize( this.WIDTH, this.HEIGHT, false );
		console.log(this.WIDTH, this.HEIGHT)
		// Put the renderer's DOM into the container
		this.renderer.domElement.id = "renderer";
		this.container.appendChild( this.renderer.domElement );
		// Set up camera and control
		this.setUpCameraAndControl();
		this.mouse = new THREE.Vector2();

		if (this.showStats) {
			this.stats = new Stats();
			this.container.appendChild( this.stats.dom );
		}

		this.addMouseEvents();

		// window resize event
		var self = this;
		$(window).on( 'resize', function(event){
			self.WIDTH = $(self.container).width(); 
			self.HEIGHT = $(self.container).height(); 
			self.renderer.setSize(self.WIDTH, self.HEIGHT)
			self.camera.aspect = self.WIDTH / self.HEIGHT;
			self.camera.updateProjectionMatrix();
			// TODO: update camera frustum, position and the x, y scales of the brush
		});
		
	},

	setUpCameraAndControl: function(){
		// set up or reset camera and zoom/pan control
		if (this.is3d){
			this.camera = new THREE.PerspectiveCamera( 70, this.aspectRatio, 0.01, 1000000 );
			// this.camera.position.z = this.pointSize * 50;
			this.camera.position.z = 30;
		} else { // 2d
			// This is the radius of the camera frustum
			ORTHO_CAMERA_FRUSTUM_HALF_EXTENT = 11.5;
			// This is the half range of the x, y coords for the visualization
			// x -> [0, 20]
			// y -> [0, 20]
			COORDS_HALF_RANGE = 10 
			// Decide camera frustum
			var left = 0,
				right = 2*ORTHO_CAMERA_FRUSTUM_HALF_EXTENT,
				bottom = -2*ORTHO_CAMERA_FRUSTUM_HALF_EXTENT,
				top = 0;
			// Scale up the larger of (w, h) to match the aspect ratio.
			var aspectRatio = this.aspectRatio;
			if (aspectRatio > 1) {
				left *= aspectRatio;
				right *= aspectRatio;
				var margin_x = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT*aspectRatio - COORDS_HALF_RANGE
				var margin_y = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT - COORDS_HALF_RANGE
				var pos_y = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT + COORDS_HALF_RANGE
			} else {
				top /= aspectRatio;
				bottom /= aspectRatio;
				var margin_x = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT - COORDS_HALF_RANGE
				var margin_y = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT/aspectRatio - COORDS_HALF_RANGE
				var pos_y = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT/aspectRatio + COORDS_HALF_RANGE
			}
			this.camera = new THREE.OrthographicCamera( left, right, top, bottom, -1000, 1000 );
			// Decide camera position
			var pos_x = -margin_x,
				pos_z = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT;
			this.camera.position.set(pos_x, pos_y, pos_z)
		}

		var self = this;
		if (!this.is3d) { // setup brush for 2d
			// flag indicating whether shiftKey is pressed
			this.shiftKey = false;

			var aspect = this.aspectRatio
			var width = this.WIDTH
			var height = this.HEIGHT

			this.svg = d3.select("#body").append('svg')
				.attr('id', 'brush')
				.attr('width', width)
				.attr('height', height)
				.style('left', 0)
				.style('top', 0)
				.style('position', 'absolute')

			// brush
			this.brush = d3.svg.brush()
				.x(d3.scale.linear().range([0, width]).domain([-margin_x, -margin_x + right]))
				.y(d3.scale.linear().range([height, 0]).domain([-margin_y, -margin_y - bottom]))
				.on('brushstart', function(){
					if (!self.shiftKey) {
						d3.event.target.clear();
						// clear previous brushed region
						d3.select(this).call(self.brush.clear())
					}
				})
				.on('brush', brushmove)
				.on('brushend', brushend);

			function brushmove(){
				if (self.shiftKey) {
					// self.removeMouseEvents()
					var extent = self.brush.extent()
					// find points intersecting with the brush box
					var intersectingIdx = [];
					for (var i = 0; i < self.clouds.length; i++) {
						var cloud = self.clouds[i]
						var idx = cloud.intersectBox(extent);
						intersectingIdx = intersectingIdx.concat(idx)
						if (idx.length > 0) {
							cloud.highlightIntersectedPoints(idx)
						}
					}
					self.renderer.render( self.scene, self.camera )
				}
			}

			function brushend(){
				var extent = self.brush.extent()
				// self.addMouseEvents()
				// find points intersecting with the brush box
				var intersectingIds = []; // this collects the 'id' attributes
				for (var i = 0; i < self.clouds.length; i++) {
					var cloud = self.clouds[i]
					var sample_ids = cloud.geometry.getAttribute('id').array
					var idx = cloud.intersectBox(extent);
					var ids = []; // collects 'id' attributes from this cloud

					for (var j = 0; j < idx.length; j++) {
						var id = sample_ids[ [idx[j]] ];
						ids.push(id)
					}

					intersectingIds = intersectingIds.concat(ids)
					if (idx.length > 0) {
						cloud.highlightIntersectedPoints(idx)
					}
				}
				self.renderer.render( self.scene, self.camera )

				if (intersectingIds.length > 0){
					self.trigger('brushended', intersectingIds)
				}
			}

			this.brush_g = this.svg.append('g')
				.datum(function() { return {selected: false, previouslySelected: false}; })
				.attr('class', 'brush')
				.call(self.brush)
				.style('pointer-events', 'none')

			// zoom and pan using d3
			// http://bl.ocks.org/nitaku/b25e6f091e97667c6cae/569c5da78cf5c51577981a7e4d9f2dc6252dbeed
			// this.view = d3.select(this.renderer.domElement);
			DZOOM = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT
			zoom = d3.behavior.zoom().scaleExtent([0.2, 10])
				.on('zoom', function() {
					if (!self.shiftKey){
						var x, y, z, _ref;
						z = zoom.scale();
						_ref = zoom.translate(), x = _ref[0], y = _ref[1];
						x = x - width / 2;
						y = y - height / 2;
						// after simplications
						var c = 2 
						self.camera.left = -DZOOM / z * aspect * (1 + c*x/width);
						self.camera.right = DZOOM / z * aspect * (1 - c*x/width);
						self.camera.top = DZOOM / z * (1 + c*y/height);
						self.camera.bottom = -DZOOM / z *(1 - c*y/height);

						self.camera.updateProjectionMatrix();

						self.brush_g.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
						self.renderer.render( self.scene, self.camera )
					}
				});
			this.svg.call(zoom)
		} else { // 3d, set up OrbitControls
			// set up orbit controls
			this.controls = new THREE.OrbitControls( this.camera, this.renderer.domElement );
			this.controls.addEventListener( 'change', function(){
				self.renderScatter()
			} );
			this.controls.enableZoom = true;
		}

		// set up raycaster, mouse
		this.raycaster = new THREE.Raycaster();
		if (this.raycasterThreshold){
			this.raycaster.params.Points.threshold = this.raycasterThreshold;
		} else{
			if (this.is3d){
				this.raycaster.params.Points.threshold = this.pointSize/5;	
			} else {
				this.raycaster.params.Points.threshold = this.pointSize/200;	
			}
		}
	},

	removeCurrentCameraAndControl: function(){
		// remove the current camera and control from the object and DOMs
		this.camera = undefined;
		this.raycaster = undefined;

		if (this.is3d){
			this.controls = undefined;
		} else {
			this.svg.remove()
			this.svg = undefined;
			this.brush_g = undefined;
		}
	},

	changeModel: function(url){
		// change model and update the visualization
		if (this.is3d){
			this.stopAnimate();
		}
		this.removeCurrentCameraAndControl()
		this.clearScene()

		var n_dim = parseInt(url.split('/').slice(-1)[0]);
		this.is3d = n_dim === 3;
		this.pointSize = this.is3d ? 0.5 : 12;

		this.model = new ScatterData({url: url})
		this.setUpCameraAndControl()

		var self = this;
		this.listenTo(this.model, 'sync', function(){
			self.shapeBy(self.shapeKey)
			if(self.is3d){
				self.animate();
			}
			self.trigger('modelChanged', url);
		});
		// use the updated model to fetch the data
		this.model.fetch()
	},

	enableBrush: function(){
		this.shiftKey = true
		this.brush_g.style('pointer-events', 'all')
	},

	disableBrush: function(){
		this.shiftKey = false
		this.brush_g.style('pointer-events', 'none')
	},

	clearBrush: function(){
		this.shiftKey = false
		this.brush_g.call(this.brush.clear())
			.style('pointer-events', 'none')
	},

	addMouseEvents: function(){
		var self = this;
		// mousemove event
		$(this.container).on( 'mousemove', function(event){
			// update mouse position
			self.mouse.x = ( event.offsetX / self.WIDTH ) * 2 - 1;
			self.mouse.y = - ( event.offsetY / self.HEIGHT ) * 2 + 1;

			self.renderScatter();

		});

		// mouseclick event
		$(this.container).mousedown(function(event){
			if (event.shiftKey) { // shift+click
				self.mouseClick();
			} else {
				if (self.is3d){
					self.stopAnimate();	
				}
			}
		});
	},

	removeMouseEvents: function(){
		$(this.container).off('mousemove');
		$(this.container).off('click');
	},

	clearClouds: function(){
		// remove all Points object in the scene
		var scene = this.scene;
		for (var i = this.clouds.length - 1; i >= 0; i--) {
			var id = this.clouds[i].points.id;
			scene.remove(scene.getObjectById(id))
		}
	},

	clearScene: function(){
		// clear everything from the scene
		var scene = this.scene;
		for (var i = scene.children.length - 1; i >= 0; i--) {
			var obj = scene.children[i];
			scene.remove(obj)
		}
	},

	shapeBy: function(metaKey){
		// groupBy the model and init clouds
		// update shapeKey
		this.shapeKey = metaKey;
		// clear this.clouds
		this.clearClouds();
		this.clouds = [];
		
		var textures = this.textures;
		var symbols = _.map(d3.svg.symbolTypes, function(t){
			return d3.svg.symbol().type(t)();});

		if (metaKey == null){
			var scatterDataSubsets = new _ScatterDataSubset({data: this.model.data});
			var cloud = new Scatter3dCloud({
				model: scatterDataSubsets,
				texture: textures.getTexture('circle'), 
				pointSize: this.pointSize,
				sizeAttenuation: this.is3d,
				labelKey: this.labelKey,
			});
			this.clouds.push(cloud)
			this.scene.add( cloud.points );	

		} else {
			// make shapeScale for d3.legend
			var meta = _.findWhere(this.model.metas, {name: metaKey});

			if (meta.type === 'number' && meta.nUnique > 6) {
				if (meta.name === 'p-value'){
					// get grouped datasets, each group is going to be a cloud
					var pValueDomain = [0.001, 0.01, 0.05, 0.1, 1];
					var scatterDataSubsets = this.model.binBy2(metaKey, pValueDomain);
					// Make a threshold scale
					var binnedValues = binValues2(_.pluck(this.model.data, metaKey), pValueDomain);
					// overwrite the symbols map to make it having the same length with pValueDomain
					var symbols = _.map(d3.svg.symbolTypes.slice(0, pValueDomain.length), function(t){
						return d3.svg.symbol().type(t)();});
				} else{
					// get grouped datasets, each group is going to be a cloud
					var scatterDataSubsets = this.model.binBy(metaKey, 6);
					// Make a threshold scale
					var binnedValues = binValues(_.pluck(this.model.data, metaKey), 6);				
				}

				this.shapeScale = d3.scale.threshold()
					.domain(binnedValues.domain)
					.range(symbols);
				this.shapeLabels = binnedValues.labels;
			} else{ // categorical data
				// get grouped datasets, each group is going to be a cloud
				var scatterDataSubsets = this.model.groupBy(metaKey);
				this.shapeLabels = undefined;
				this.shapeScale = d3.scale.ordinal()
					.domain(Object.keys(scatterDataSubsets))
					.range(symbols);			
			};

			
			// symbolTypeScale is used for retrieving a texture instance from textures collection
			var symbolTypeScale = d3.scale.ordinal()
				.domain(Object.keys(scatterDataSubsets))
				.range(textures.pluck('symbolType'));
			
			for (var key in scatterDataSubsets){
				var cloud = new Scatter3dCloud({
					model: scatterDataSubsets[key],
					texture: textures.getTexture(symbolTypeScale(key)), 
					pointSize: this.pointSize,
					sizeAttenuation: this.is3d,
					labelKey: this.labelKey,
				});

				this.clouds.push(cloud)
				this.scene.add( cloud.points );	
			}

		}

		// re-coloring nodes
		this.colorBy(this.colorKey);
		if (this.colorKey === 'Scores'){ this.highlightTopNScores(5); }
		this.trigger('shapeChanged')
		this.renderScatter();

	},

	renderScatter: function(){
		// update the picking ray with the camera and mouse position
		this.raycaster.setFromCamera( this.mouse, this.camera );

		// calculate objects intersecting the picking ray
		var allPoints = _.map(this.clouds, function(obj){ return obj.points; });
		var intersects = this.raycaster.intersectObjects( allPoints );

		// reset colors
		this.resetColors();

		// remove text-label if exists
		var textLabel = document.getElementById('text-label')
		if (textLabel){
		    textLabel.remove();
		}

		// add interactivities if there is intesecting points
		if ( intersects.length > 0 ) {
			// only highlight the closest object
			var intersect = intersects[0];
			var idx = intersect.index;
			var geometry = intersect.object.geometry;
			
			// change color of the point
			geometry.attributes.color.needsUpdate = true;

			geometry.attributes.color.array[idx*3] = 0.1;
			geometry.attributes.color.array[idx*3+1] = 0.8;
			geometry.attributes.color.array[idx*3+2] = 0.1;
			// geometry.computeBoundingSphere();
			// intersect.object.updateMatrix();

			// find the position of the point
			var pointPosition = { 
			    x: geometry.attributes.position.array[idx*3],
			    y: geometry.attributes.position.array[idx*3+1],
			    z: geometry.attributes.position.array[idx*3+2],
			}

			var euler = this.clouds[0].points.rotation;
			// add text canvas
			var textCanvas = this.makeTextCanvas( geometry.attributes.label.array[idx], 
			    pointPosition.x, pointPosition.y, pointPosition.z, euler,
			    { fontsize: 18, fontface: "'Rubik', sans-serif", textColor: {r:0, g:0, b:0, a:0.8} }); 

			textCanvas.id = "text-label"
			this.container.appendChild(textCanvas);

			// geometry.computeBoundingSphere();
		}

		this.renderer.domElement.width = this.WIDTH
		this.renderer.domElement.height = this.HEIGHT
		this.renderer.render( this.scene, this.camera );

		if (this.showStats){
			this.stats.update();	
		}
	},

	mouseClick: function(){
		// find points and redirect to new location

		// update the picking ray with the camera and mouse position
		this.raycaster.setFromCamera( this.mouse, this.camera );
		// stop animation
		this.stopAnimate();

		// calculate objects intersecting the picking ray
		var allPoints = _.map(this.clouds, function(obj){ return obj.points; });
		var intersects = this.raycaster.intersectObjects( allPoints );

		if ( intersects.length > 0 ) {
			var intersect = intersects[0];
			var idx = intersect.index;
			var geometry = intersect.object.geometry;
			var id = geometry.attributes.id.array[idx];
			var url = 'sample/' + id;
			// console.log(id)
			window.open(url);
		}
	},

	makeTextCanvas: function(message, x, y, z, euler, parameters){

		if ( parameters === undefined ) parameters = {}; 
		var fontface = parameters.hasOwnProperty("fontface") ?  
			parameters["fontface"] : "arial, sans-serif";      
		var fontsize = parameters.hasOwnProperty("fontsize") ?  
			parameters["fontsize"] : 18; 
		var textColor = parameters.hasOwnProperty("textColor") ? 
			parameters["textColor"] : { r:0, g:0, b:255, a:0.8 }; 
		var lineHeight = parameters.hasOwnProperty("lineHeight") ?
			parameters["lineHeight"] : 20;

		var canvas = document.createElement('canvas'); 
		var context = canvas.getContext('2d'); 

		canvas.width = this.WIDTH; 
		canvas.height = this.HEIGHT; 

		context.font = fontsize + "px " + fontface; 
		context.textBaseline = "alphabetic"; 

		context.textAlign = "left"; 
		// get size data (height depends only on font size) 
		var metrics = context.measureText( message ); 
		var textWidth = metrics.width; 

		// text color.  Note that we have to do this AFTER the round-rect as it also uses the "fillstyle" of the canvas 
		context.fillStyle = getCanvasColor(textColor); 

		// calculate the project of 3d point into 2d plain
		var point = new THREE.Vector3(x, y, z).applyEuler(euler);
		var pv = new THREE.Vector3().copy(point).project(this.camera);
		var coords = {
			x: ((pv.x + 1) / 2 * this.WIDTH), // * this.DPR, 
			y: -((pv.y - 1) / 2 * this.HEIGHT), // * this.DPR
		};
		// draw the text (in multiple lines)
		var lines = message.split('\n');
		for (var i = 0; i < lines.length; i++) {
			context.fillText(lines[i], coords.x, coords.y + (i*lineHeight))
		};

		// styles of canvas element
		canvas.style.left = 0;
		canvas.style.top = 0;
		canvas.style.position = 'absolute';
		canvas.style.pointerEvents = 'none';

		return canvas;
	},

	resetColors: function(){
		// reset colors based on this.metaKey, do not trigger any events.
		for (var i = this.clouds.length - 1; i >= 0; i--) {
			var cloud = this.clouds[i];
			cloud.setColors(this.colorScale, this.colorKey)
		};
	},

	animate: function(){
		this.animateId = requestAnimationFrame(this.animate.bind(this))
		this.rotate()
	},

	rotate: function(){
		// rotate everything on the scene
		var time = Date.now() * 0.001;
		for (var i = this.scene.children.length - 1; i >= 0; i--) {
			var object = this.scene.children[i];
			object.rotation.x = time * 0.05;
			object.rotation.y = time * 0.1;
		}
		this.renderScatter()
	},

	stopAnimate: function(){
		cancelAnimationFrame( this.animateId );
	},

	colorBy: function(metaKey){
		// Color points by a certain metaKey
		// update colorKey
		this.colorKey = metaKey;

		var metas = this.model.getAttr(metaKey);

		var meta = _.findWhere(this.model.metas, {name: metaKey});
		var dtype = meta.type;
		
		if (dtype !== 'float' && dtype !== 'int' && meta.nUnique > 20){
			metas = encodeRareCategories(metas, 19);
		}
		var uniqueCats = new Set(metas);
		var nUniqueCats = uniqueCats.size;
		uniqueCats = Array.from(uniqueCats);
		var nullColor = '#7f7f7f';
		// Make unknown to be gray 
		if (uniqueCats.indexOf('unknown') !== -1) {
			if(uniqueCats.length > 7){
				var idx = uniqueCats.indexOf('unknown');
				greyIdx = 7;
				if (uniqueCats.length == 20){
					var greyIdx = 15;
				}
				var elem = uniqueCats[greyIdx];
				uniqueCats[greyIdx] = 'unknown';
				uniqueCats[idx] = elem;
			}
		};
		// Make RARE to be grey
		if (uniqueCats.indexOf(RARE) !== -1) {
			if (uniqueCats.length == 20){
				var idx = uniqueCats.indexOf(RARE);
				var greyIdx2 = 15;
				if (uniqueCats.indexOf('unknown') !== -1){
					var greyIdx2 = 14;
				}
				var elem = uniqueCats[greyIdx2];
				uniqueCats[greyIdx2] = RARE;
				uniqueCats[idx] = elem;
			}
		}
		// make colorScale
		if (meta.name === 'Scores') { // similarity scores should center at 0
			var colorExtent = d3.extent(metas);
			var colorScale = d3.scale.pow()
				.domain([colorExtent[0], 0, colorExtent[1]])
				.range(["#1f77b4", "#ddd", "#d62728"]);
		} else if (dtype === 'boolean'){
			var colorScale = d3.scale.ordinal().domain([true, false]).range(['#cc0000', '#cccccc']);
		} else if (nUniqueCats < 11 && dtype !== 'float'){
			var colorScale = d3.scale.category10().domain(uniqueCats);
		} else if (nUniqueCats > 10 && nUniqueCats <= 20 && dtype !== 'float') {
			var colorScale = d3.scale.category20().domain(uniqueCats);
		} else if(nUniqueCats <= 40 && dtype !== 'float'){
			var colors40 = ["#1b70fc", "#faff16", "#d50527", "#158940", "#f898fd", "#24c9d7", "#cb9b64", "#866888", "#22e67a", "#e509ae", "#9dabfa", "#437e8a", "#b21bff", "#ff7b91", "#94aa05", "#ac5906", "#82a68d", "#fe6616", "#7a7352", "#f9bc0f", "#b65d66", "#07a2e6", "#c091ae", "#8a91a7", "#88fc07", "#ea42fe", "#9e8010", "#10b437", "#c281fe", "#f92b75", "#07c99d", "#a946aa", "#bfd544", "#16977e", "#ff6ac8", "#a88178", "#5776a9", "#678007", "#fa9316", "#85c070", "#6aa2a9", "#989e5d", "#fe9169", "#cd714a", "#6ed014", "#c5639c", "#c23271", "#698ffc", "#678275", "#c5a121", "#a978ba", "#ee534e", "#d24506", "#59c3fa", "#ca7b0a", "#6f7385", "#9a634a", "#48aa6f", "#ad9ad0", "#d7908c", "#6a8a53", "#8c46fc", "#8f5ab8", "#fd1105", "#7ea7cf", "#d77cd1", "#a9804b", "#0688b4", "#6a9f3e", "#ee8fba", "#a67389", "#9e8cfe", "#bd443c", "#6d63ff", "#d110d5", "#798cc3", "#df5f83", "#b1b853", "#bb59d8", "#1d960c", "#867ba8", "#18acc9", "#25b3a7", "#f3db1d", "#938c6d", "#936a24", "#a964fb", "#92e460", "#a05787", "#9c87a0", "#20c773", "#8b696d", "#78762d", "#e154c6", "#40835f", "#d73656", "#1afd5c", "#c4f546", "#3d88d8", "#bd3896", "#1397a3", "#f940a5", "#66aeff", "#d097e7", "#fe6ef9", "#d86507", "#8b900a", "#d47270", "#e8ac48", "#cf7c97", "#cebb11", "#718a90", "#e78139", "#ff7463", "#bea1fd"];
			var colorScale = d3.scale.ordinal().range(colors40).domain(uniqueCats)
		} else {
			var colorExtent = d3.extent(metas);
			var min_score = colorExtent[0],
				max_score = colorExtent[1];
			var colorScale = d3.scale.pow()
				.domain([min_score, (min_score+max_score)/2, max_score])
				.range(["#1f77b4", "#ddd", "#d62728"]);
		}
		
		if (meta.hasNull){
			var colorScaleWrapper = function(item){
				c = colorScale(item)
				if (item === null){
					var c = nullColor;
				}
				return c;
			}
			colorScaleWrapper.domain = colorScale.domain
			colorScaleWrapper.range = colorScale.range
			colorScaleWrapper.rangeRound = colorScale.rangeRound
			colorScaleWrapper.interpolate = colorScale.interpolate
			colorScaleWrapper.exponent = colorScale.exponent
			colorScaleWrapper.ticks = colorScale.ticks
			colorScaleWrapper.tickFormat = colorScale.tickFormat

			this.colorScale = colorScaleWrapper
		} else {
			this.colorScale = colorScale; // the d3 scale used for coloring nodes	
		}
		this.colorScale.hasNull = meta.hasNull
		this.colorScale.nullColor = nullColor
		this.colorScale.dtype = meta.type
		this.colorScale.nUnique = meta.nUnique

		this.trigger('colorChanged');
		this.renderScatter();
	},

	colorByScoresFromUrl: function(url, term){
		var self = this;
		$.getJSON(url + '/' + term, function(result){
			self.colorKey = term;
			self.model.setAttr(term, result[term]);
			self.shapeBy(self.shapeKey)
		});
	},

	colorByCategoriesFromUrl: function(url, obj){
		var attrName = obj.name + '/' + obj.type;
		if (this.labelKey.indexOf(attrName) === -1){
			// retrieve from server if not in the labelKey
			var self = this;
			$.getJSON(url + '/' + attrName, function(result){
				self.colorKey = obj.name + '/' + obj.type;
				self.model.setAttr(attrName, result[obj.name]);
				// Add this lib to labelKey for hovering display
				self.labelKey.push(attrName);
				self.shapeBy(self.shapeKey)
			});
		} else{
			this.colorKey = attrName;
			this.shapeBy(this.shapeKey)
		}
	},

});
