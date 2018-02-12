/*
The models and views for the scatter plot.
*/

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
		// this.geometry.addAttribute( 'pert_id', new THREE.BufferAttribute( model.getAttr('pert_id'), 1 ) );
		this.geometry.addAttribute( 'sig_id', new THREE.BufferAttribute( model.getAttr('sig_id'), 1 ) )

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
		return this.attributes.url + '?n=' + this.n;
	},

	parse: function(response){
		// called whenever a model's data is returned by the server
		this.n = response.length;
		var xyz = ['x', 'y', 'z'];
		for (var key in response[0]){
			if (xyz.indexOf(key) === -1){ 
				var nUnique = _.unique(_.pluck(response, key)).length;
				var type = typeof response[0][key];
				this.metas.push({
					name: key,
					nUnique: nUnique,
					type: type,
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
		// fetch json data from server
		this.fetch();
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
			type: typeof values[0]
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
		shapeKey: 'cell',
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
				console.log('model synced')
				self.setUpStage();
				// self.colorBy(self.colorKey);
				self.shapeBy(self.shapeKey);

			});
		});
	},

	setUpStage: function(){
		// set up THREE.js visualization components
		this.aspectRatio = this.WIDTH / this.HEIGHT;
		
		// set up scene, camera, renderer
		this.scene = new THREE.Scene();
		// this.scene.fog = new THREE.FogExp2( 0xcccccc, 0.002 );

		this.renderer = new THREE.WebGLRenderer();
		// this.renderer.setClearColor( this.scene.fog.color );
		// this.renderer.setClearColor( 0xcccccc );
		this.renderer.setClearColor( 0xffffff );
		this.renderer.setPixelRatio( this.DPR );
		this.renderer.setSize( this.WIDTH, this.HEIGHT );

		if (this.is3d){
			this.camera = new THREE.PerspectiveCamera( 70, this.aspectRatio, 0.01, 1000000 );
			this.camera.position.z = this.pointSize * 120;
		} else { // 2d
			ORTHO_CAMERA_FRUSTUM_HALF_EXTENT = 10.5;
			var left = -ORTHO_CAMERA_FRUSTUM_HALF_EXTENT;
			var right = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT;
			var bottom = -ORTHO_CAMERA_FRUSTUM_HALF_EXTENT;
			var top = ORTHO_CAMERA_FRUSTUM_HALF_EXTENT;
			// Scale up the larger of (w, h) to match the aspect ratio.
			var aspectRatio = this.aspectRatio;
			if (aspectRatio > 1) {
				left *= aspectRatio;
				right *= aspectRatio;
			} else {
				top /= aspectRatio;
				bottom /= aspectRatio;
			}
			this.camera = new THREE.OrthographicCamera( left, right, top, bottom, -1000, 1000 );
		}

		// Put the renderer's DOM into the container
		this.renderer.domElement.id = "renderer";
		this.container.appendChild( this.renderer.domElement );

		var self = this;
		// set up orbit controls
		this.controls = new THREE.OrbitControls( this.camera, this.renderer.domElement );
		this.controls.addEventListener( 'change', function(){
			self.renderScatter()
		} );
		this.controls.enableZoom = true;
		
		if (!this.is3d){
			this.controls.mouseButtons.ORBIT = null;
			this.controls.enableRotate = false;
			this.controls.mouseButtons.PAN = THREE.MOUSE.LEFT;			
		}
		// this.controls.dampingFactor = 0.5;

		// this.controls = new THREE.TrackballControls( this.camera );
		// this.controls.rotateSpeed = 1.0;
		// this.controls.zoomSpeed = 1.2;
		// this.controls.panSpeed = 0.8;
		// this.controls.noZoom = false;
		// this.controls.noPan = false;
		// this.controls.staticMoving = true;
		// this.controls.dynamicDampingFactor = 0.3;

		// set up raycaster, mouse
		this.raycaster = new THREE.Raycaster();
		if (this.raycasterThreshold){
			this.raycaster.params.Points.threshold = this.raycasterThreshold;
		} else{
			if (this.is3d){
				this.raycaster.params.Points.threshold = this.pointSize/5;	
			} else {
				this.raycaster.params.Points.threshold = this.pointSize/500;	
			}			
		}
		
		this.mouse = new THREE.Vector2();

		if (this.showStats) {
			this.stats = new Stats();
			this.container.appendChild( this.stats.dom );
		}

		this.addMouseEvents();

		// window resize event
		$(window).on( 'resize', function(event){
			self.WIDTH = $(self.container).width(); 
			self.HEIGHT = $(self.container).height(); 
			self.camera.aspect = self.WIDTH / self.HEIGHT;
			self.camera.updateProjectionMatrix();
			self.renderer.setSize(self.WIDTH, self.HEIGHT)
		});
		
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
		$(this.container).click(function(event){
			self.mouseClick();
		});

	},

	removeMouseEvents: function(){
		$(this.container).off('mousemove');
		$(this.container).off('click');
	},

	clearScene: function(){
		// remove everythin in the scene
		var scene = this.scene;
		for( var i = scene.children.length - 1; i >= 0; i--) {
			scene.remove(scene.children[i]);
		}
	},

	shapeBy: function(metaKey){
		// groupBy the model and init clouds
		// update shapeKey
		this.shapeKey = metaKey;
		// clear this.clouds
		this.clouds = [];
		this.clearScene();
		
		var textures = this.textures;
		var symbols = _.map(d3.svg.symbolTypes, function(t){
			return d3.svg.symbol().type(t)();});

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
			// console.log(intersects)
			// only highlight the closest object
			var intersect = intersects[0];
			// console.log(intersect)
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

			// add text canvas
			var textCanvas = this.makeTextCanvas( geometry.attributes.label.array[idx], 
			    pointPosition.x, pointPosition.y, pointPosition.z,
			    { fontsize: 24, fontface: "arial, sans-serif", textColor: {r:0, g:0, b:0, a:0.8} }); 

			textCanvas.id = "text-label"
			this.container.appendChild(textCanvas);

			// geometry.computeBoundingSphere();
		}

		this.renderer.render( this.scene, this.camera );

		if (this.showStats){
			this.stats.update();	
		}
	},

	mouseClick: function(){
		// find points and redirect to new location

		// update the picking ray with the camera and mouse position
		this.raycaster.setFromCamera( this.mouse, this.camera );

		// calculate objects intersecting the picking ray
		var allPoints = _.map(this.clouds, function(obj){ return obj.points; });
		var intersects = this.raycaster.intersectObjects( allPoints );

		if ( intersects.length > 0 ) {
			var intersect = intersects[0];
			var idx = intersect.index;
			var geometry = intersect.object.geometry;
			// var pert_id = geometry.attributes.pert_id.array[idx];
			// var url = 'http://amp.pharm.mssm.edu/dmoa/report/' + pert_id;
			var sig_id = geometry.attributes.sig_id.array[idx];
			var url = 'http://amp.pharm.mssm.edu/dmoa/sig/' + sig_id;
			window.open(url);
		}
	},

	makeTextCanvas: function(message, x, y, z, parameters){

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
		var point = new THREE.Vector3(x, y, z);
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

	colorBy: function(metaKey){
		// Color points by a certain metaKey
		// update colorKey
		this.colorKey = metaKey;

		var metas = this.model.getAttr(metaKey);

		var meta = _.findWhere(this.model.metas, {name: metaKey});
		var dtype = meta.type;
		
		if (dtype !== 'number' && meta.nUnique > 20){
			metas = encodeRareCategories(metas, 19);
		}
		var uniqueCats = new Set(metas);
		var nUniqueCats = uniqueCats.size;
		uniqueCats = Array.from(uniqueCats);
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
		} else if (nUniqueCats < 11){
			var colorScale = d3.scale.category10().domain(uniqueCats);
		} else if (nUniqueCats > 10 && nUniqueCats <= 20) {
			var colorScale = d3.scale.category20().domain(uniqueCats);
		} else if(nUniqueCats <= 40){
			var colors40 = ["#1b70fc", "#faff16", "#d50527", "#158940", "#f898fd", "#24c9d7", "#cb9b64", "#866888", "#22e67a", "#e509ae", "#9dabfa", "#437e8a", "#b21bff", "#ff7b91", "#94aa05", "#ac5906", "#82a68d", "#fe6616", "#7a7352", "#f9bc0f", "#b65d66", "#07a2e6", "#c091ae", "#8a91a7", "#88fc07", "#ea42fe", "#9e8010", "#10b437", "#c281fe", "#f92b75", "#07c99d", "#a946aa", "#bfd544", "#16977e", "#ff6ac8", "#a88178", "#5776a9", "#678007", "#fa9316", "#85c070", "#6aa2a9", "#989e5d", "#fe9169", "#cd714a", "#6ed014", "#c5639c", "#c23271", "#698ffc", "#678275", "#c5a121", "#a978ba", "#ee534e", "#d24506", "#59c3fa", "#ca7b0a", "#6f7385", "#9a634a", "#48aa6f", "#ad9ad0", "#d7908c", "#6a8a53", "#8c46fc", "#8f5ab8", "#fd1105", "#7ea7cf", "#d77cd1", "#a9804b", "#0688b4", "#6a9f3e", "#ee8fba", "#a67389", "#9e8cfe", "#bd443c", "#6d63ff", "#d110d5", "#798cc3", "#df5f83", "#b1b853", "#bb59d8", "#1d960c", "#867ba8", "#18acc9", "#25b3a7", "#f3db1d", "#938c6d", "#936a24", "#a964fb", "#92e460", "#a05787", "#9c87a0", "#20c773", "#8b696d", "#78762d", "#e154c6", "#40835f", "#d73656", "#1afd5c", "#c4f546", "#3d88d8", "#bd3896", "#1397a3", "#f940a5", "#66aeff", "#d097e7", "#fe6ef9", "#d86507", "#8b900a", "#d47270", "#e8ac48", "#cf7c97", "#cebb11", "#718a90", "#e78139", "#ff7463", "#bea1fd"];
			var colorScale = d3.scale.ordinal().range(colors40).domain(uniqueCats)
		} else {
			var colorExtent = d3.extent(metas);
			var min_score = colorExtent[0],
				max_score = colorExtent[1];
			var colorScale = d3.scale.pow()
				.domain([min_score, (min_score+max_score)/2, max_score])
				.range(["#1f77b4", "#ddd", "#d62728"]);
			// var shifted_max = max_score + 1 - min_score;

		}

		this.colorScale = colorScale; // the d3 scale used for coloring nodes

		this.trigger('colorChanged');
		this.renderScatter();
	},

	colorByScores: function(searchResult){
		// To color nodes by similarity scores. 
		// The input is the response from the /search endpoint.
		this.colorKey = 'scores';
		// store the scores in the model
		this.model.setAttr('scores', searchResult.scores);
		// update the clouds by calling shapeBy
		this.shapeBy(this.shapeKey);
	},

	highlightQuery: function(query, metaKey){
		// To highlight a query result, red for matched nodes and grey for unmatched nodes
		this.colorKey = metaKey;
		this.colorScale = function(x) {
			return x === query ? "#cc0000" : "#cccccc";
		};
		this.renderScatter();
	},

	createHighlightCloud: function(dataSubset){
		// Create a Scatter3dCloud for a _ScatterDataSubset instance
		var highlightCould = new Scatter3dCloud({
			model: dataSubset,
			texture: this.textures.getTexture('circle'), 
			pointSize: this.pointSize * 5,
			sizeAttenuation: this.is3d,
			opacity: 0.4	
		});
		return highlightCould;
	},

	highlightQuery2: function(query, metaKey){
		// To highlight a query result by adding a new Scatter3dCloud instance
		var scatterDataSubsets = this.model.groupBy(metaKey);
		this.highlightCould = this.createHighlightCloud(scatterDataSubsets[query])
		this.highlightCould.setSingleColor('yellow');
		this.highlightCould.points.name = 'highlight';
		this.scene.add(this.highlightCould.points)
		this.renderScatter();

	},

	highlightTopNScores: function(n){
		var sortedData = _.sortBy(this.model.data, 'Scores')
		// var dataSubsetsToHighlight = sortedData.slice(0, n).concat(sortedData.slice(-n))
		// var scatterDataSubsetsToHighlight = new _ScatterDataSubset({data: dataSubsetsToHighlight})
		// this.highlightCould = new Scatter3dCloud({
		// 	model: scatterDataSubsetsToHighlight,
		// 	texture: this.textures.getTexture('circle'), 
		// 	pointSize: this.pointSize * 5,
		// 	sizeAttenuation: this.is3d,
		// 	opacity: 0.4
		// })

		this.highlightCouldNeg = this.createHighlightCloud(
			new _ScatterDataSubset({data: sortedData.slice(0, n)}))
		this.highlightCouldNeg.setSingleColor('#62fff7');
		this.highlightCouldNeg.points.name = 'highlight-neg';
		this.scene.add(this.highlightCouldNeg.points)

		this.highlightCouldPos = this.createHighlightCloud(
			new _ScatterDataSubset({data: sortedData.slice(-n)}))
		this.highlightCouldPos.setSingleColor('#f463ff');
		this.highlightCouldPos.points.name = 'highlight-pos';
		this.scene.add(this.highlightCouldPos.points)

		this.renderScatter();

	},

	removeHighlightedPoints: function(){
		var scene = this.scene;
		scene.remove(scene.getObjectByName('highlight'));
		this.highlightCould = undefined;
		scene.remove(scene.getObjectByName('highlight-neg'));
		this.highlightCouldNeg = undefined;
		scene.remove(scene.getObjectByName('highlight-pos'));
		this.highlightCouldPos = undefined;
		this.renderScatter();
	}

	// sizeBy: function(metaKey){
	// 	// Size points by a certain metaKey
	// 	var metas = this.model.meta[metaKey]
	// 	var sizeExtent = d3.extent(metas)
	// 	var sizeScale = d3.scale.linear()
	// 		.domain(sizeExtent)
	// 		.range([0.1, 4]);
	// 	// construct sizes BufferAttribute
	// 	var sizes = _.map(sizeScale, metas); 

	// 	this.sizes = sizes;

	// 	this.geometry.addAttribute( 'size', new THREE.BufferAttribute( sizes, 1 ) );
	// 	this.geometry.attributes.size.needsUpdate = true;

	// 	this.renderer.render( this.scene, this.camera );
	// }

});

