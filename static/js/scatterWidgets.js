/*
The widgets for the interactive scatter plot.
*/

var Legend = Backbone.View.extend({
	// A view for the legends of the Scatter3dView
	// tagName: 'svg',
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		w: '300px',
		h: '800px',
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		this.setUpDOMs();
		// render if the scatterPlot changed
		this.listenTo(this.scatterPlot, 'shapeChanged', this.render)
		this.listenTo(this.scatterPlot, 'colorChanged', this.render)
	},

	setUpDOMs: function(){
		// set up DOMs for the legends
		this.el = d3.select(this.container)
			.append('svg')
			.attr('id', 'legend')
			.attr('width', this.w)
			.attr('height', this.h);

		this.g = this.el.append('g')
			.attr('class', 'legend')
			.attr('transform', 'translate(10, 20)');
		this.g.append('g')
			.attr('id', 'legendColor')
			.attr("class", "legendPanel")
			.attr("transform", "translate(0, 0)")
			.attr("visibility", "hidden");
		this.g.append('g')
			.attr('id', 'legendShape')
			.attr("class", "legendPanel")
			.attr("transform", "translate(0, 0)")
			.attr("visibility", "hidden");
		this.g.append('g')
			.attr('id', 'legendAxis')
			.attr("class", "legendPanel")
			.attr("transform", "translate(0, 0)")
			.attr("visibility", "hidden");

	},

	render: function(){
		// set up legend
		var scatterPlot = this.scatterPlot;
		if (scatterPlot.shapeKey != null){
			// shape legend
			var legendShape = d3.legend.symbol()
				.scale(scatterPlot.shapeScale)
				.orient("vertical")
				.title(scatterPlot.shapeKey);
			if (scatterPlot.shapeLabels){
				legendShape.labels(scatterPlot.shapeLabels)
			}
			this.g.select("#legendShape")
				.call(legendShape);			
		}

		// color legend
		var legendColor = d3.legend.color()
			.title(scatterPlot.colorKey)
			.shapeWidth(20)
			.cells(5)
			.labelFormat(d3.format(".2f"))
			.scale(scatterPlot.colorScale);

		this.g.select("#legendColor")
			.call(legendColor);

		// gross hack
		const legend_base = $('#vis-btn-group > .btn-group > .btn.active')[0].id
			// end gross hack

		// axis legend
		if (this.scatterPlot.is3d) {
			var legendScale = d3.scale.ordinal()
				.domain([`${legend_base}-1`, `${legend_base}-2`, `${legend_base}-3`])
				.range(["#ff0000", "#00ff00", "#0000ff"])
			var legendAxis = d3.legend.color()
				.title("Axes")
				.shapeWidth(20)
				.cells(3)
				.scale(legendScale)

			this.g.select("#legendAxis")
				.call(legendAxis)
		} else {
			var legendScale = d3.scale.ordinal()
				.domain([`${legend_base}-1`, `${legend_base}-2`])
				.range(["#ff0000", "#00ff00"])
			var legendAxis = d3.legend.color()
				.title("Axes")
				.shapeWidth(20)
				.cells(3)
				.scale(legendScale)

			this.g.select("#legendAxis")
				.call(legendAxis)
		}

		var self = this
		// a hack here because d3.legend has no callback
		setTimeout(function(){self.createLegendCellForNull();}, 400)
		setTimeout(function(){self.moveShapeLegend();}, 500)

		return this;
	},
	
	moveShapeLegend: function(){
		var legendColorBBox = this.g.select('#legendColor').node().getBBox();
		var legendShapeBBox = this.g.select('#legendShape').node().getBBox();
		// show legendColor accordingly
		this.g.select('#legendColor')
			.transition()
			.attr("visibility", "visible")
			.duration(100)
		// move legendShape accordingly
		this.g.select('#legendShape')
			.transition()
			.attr('transform', 'translate(0, ' + legendColorBBox.height + 10 + ')')
			.attr("visibility", "visible")
			.duration(100)
		
		// move legendAxis accordingly
		this.g.select('#legendAxis')
			.transition()
			.attr('transform', 'translate(0, ' + (legendColorBBox.height + 10 + legendShapeBBox.height + 10) + ')')
			.attr("visibility", "visible")
			.duration(100)
	},

	createLegendCellForNull: function(){
		// A hacky method to add legend cell for null values
		var colorScale = this.scatterPlot.colorScale;
		if (colorScale.hasNull){
			if (colorScale.dtype === 'float'|| (colorScale.dtype === 'int' && colorScale.nUnique > 40)){
				// select the second legend cell to get the translate value
				var legendCell = this.g.select("#legendColor").select('.cell:nth-child(2)');
				var nCells = this.g.select("#legendColor").selectAll('.cell')[0].length;
				var ty = d3.transform(legendCell.attr('transform')).translate[1]
				var nullCell = this.g.select("#legendColor")
					.select('.legendCells')
					.append('g').attr('class', 'cell')
					.attr('transform', 'translate(0, '+ty * nCells+')')
				// get size of the rect
				var h = legendCell.select('rect').attr('height'),
					w = legendCell.select('rect').attr('width'),
					t = d3.transform(legendCell.select('text').attr('transform')).translate;
				nullCell.append('rect')
					.attr('class', 'swatch')
					.attr('height', h)
					.attr('width', w)
					.style('fill', colorScale.nullColor)
				nullCell.append('text')
					.attr('class', 'label')
					.attr('transform', 'translate('+t[0]+', '+t[1]+')')
					.text('N/A')
			} else { // Add "N/A" to the legend cell with empty text
				this.g.select("#legendColor").selectAll('.cell text').each(function(){
					var legendText = d3.select(this).text();
					if (legendText === ''){
						d3.select(this).text('N/A')
					}
				});
			}
		}
	},
});

// This is a map for the tooltips displayed to explain the 
// colorBy and shapeBy options.
var tooltipTexts = { 
};

var Controler = Backbone.View.extend({

	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		w: 300,
		h: 800,
		inferredMeta: [], // a list of metadata names inferred by us
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.listenTo(this.scatterPlot.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		var self = this;
		this.listenTo(scatterPlot, 'shapeChanged', this.changeSelection)

		scatterPlot.listenTo(this, 'shapeChanged', function(selectedMetaKey){
			if (selectedMetaKey != self.scatterPlot.shapeKey){
				scatterPlot.shapeBy(selectedMetaKey);	
			}
		});
		scatterPlot.listenTo(this, 'colorChanged', function(selectedMetaKey){
			if (selectedMetaKey != self.scatterPlot.colorKey){
				scatterPlot.colorBy(selectedMetaKey);
			}
		});
		// update options when model changed
		this.listenTo(scatterPlot, 'modelChanged', this.updateOptions)
	},

	render: function(){
		// set up DOMs for the controler
		this.el = d3.select(this.container)
			.append('div')
			.attr('id', 'controls')
			.style('width', this.w)
			.style('height', this.h);

		this.setUpDOMs();

		return this;
	},

	setUpDOMs: function() {
		var self = this;
		// Shapes: 
		this.shapeControl = this.el.append('div')
			.attr('class', 'form-group my-1');
		this.shapeControl.append('label')
			.attr('class', 'control-label')
			.text('Shape by:');

		this.shapeSelect = this.shapeControl.append('select')
			.attr('id', 'shape')
			.attr('class', 'form-control selectpicker control-picker')
			.on('change', function(){
				var selectedMetaKey = d3.select('#shape').property('value');
				self.trigger('shapeChanged', selectedMetaKey)
			});

		// Colors
		this.colorControl = this.el.append('div')
			.attr('class', 'form-group my-1')
		this.colorControl.append('label')
			.attr('class', 'control-label')
			.text('Color by:');

		this.colorSelect = this.colorControl.append('select')
			.attr('id', 'color')
			.attr('class', 'form-control selectpicker control-picker')
			.on('change', function(){
				var selectedMetaKey = d3.select('#color').property('value');
				self.trigger('colorChanged', selectedMetaKey)
			});

		this.updateOptions()
	},

	updateOptions: function(){
		// update options using this.sdv.models.metas
		this.removeCurrentOptions()

		var model = this.scatterPlot.model;
		var inferredMeta = this.inferredMeta;
		// filter out metas used as index
		var metas = _.filter(model.metas, function(meta){ return meta.nUnique < model.n || meta.type === 'float'; });
		var metasShape = _.filter(metas, function(meta){ return meta.nUnique < 7 });

		var metasColor = _.partition(_.pluck(metas, 'name'), function(name){
			return inferredMeta.indexOf(name) === -1;
		})

		if (metasShape.length > 0){
			metasShape = _.partition(_.pluck(metasShape, 'name'), function(name){
				return inferredMeta.indexOf(name) === -1;
			});
			this.shapeOptGroup1 = this.shapeSelect
				.append('optgroup')
				.attr('label', 'User-provided metadata')
					.selectAll('option')
					.data(metasShape[0]).enter()
					.append('option')
					.text(function(d){return d;})
					.attr('value', function(d){return d;});
			this.shapeOptGroup2 = this.shapeSelect
				.append('optgroup')
				.attr('label', 'Inferred metadata')
					.selectAll('option')
					.data(metasShape[1]).enter()
					.append('option')
					.text(function(d){return d;})
					.attr('value', function(d){return d;});
		}

		this.colorOptGroup1 = this.colorSelect
			.append('optgroup')
			.attr('label', 'User-provided metadata')
				.selectAll('option')
				.data(metasColor[0]).enter()
				.append('option')
				.text(function(d){return d;})
				.attr('value', function(d){return d;})

		this.colorOptGroup2 = this.colorSelect
			.append('optgroup')
			.attr('label', 'Inferred metadata')
				.selectAll('option')
				.data(metasColor[1]).enter()
				.append('option')
				.text(function(d){return d;})
				.attr('value', function(d){return d;})

		$('.control-picker').selectpicker({
			style: 'btn-outline-secondary btn-sm',
		});
		$('.control-picker').selectpicker('refresh');
	},

	changeSelection: function(){
		// change the current selected option to value
		$('#shape').val(this.scatterPlot.shapeKey); 
		$('#color').val(this.scatterPlot.colorKey);
		$('.control-picker').selectpicker('refresh');
	},

	removeCurrentOptions: function(){
		// remove all current options if exists
		if(this.colorOptGroup1){
			var currentOptions = this.colorOptGroup1.data().concat(this.colorOptGroup2.data())
			for (var i = currentOptions.length - 1; i >= 0; i--) {
				var op = currentOptions[i]
				$('#color').find('[value="'+op+'"]').remove()
			}
		}

		if (this.shapeOptGroup1){
			var currentOptions = this.shapeOptGroup1.data().concat(this.shapeOptGroup2.data())
			for (var i = currentOptions.length - 1; i >= 0; i--) {
				var op = currentOptions[i]
				$('#shape').find('[value="'+op+'"]').remove()
			}
		}
	},

});

var SearchSelectize = Backbone.View.extend({
	// selectize to search for genes by name
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		synonymsUrl: 'query_genes', // the url to retrieve available options
		retrieveUrl: 'get_gene', // the url to retrieve a single item
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot highlightQuery once selectize is searched
		var retrieveUrl = this.retrieveUrl;
		scatterPlot.listenTo(this, 'searched', function(query){
			scatterPlot.colorByScoresFromUrl(retrieveUrl, query);
		});

	},

	render: function(){
		// set up the DOMs
		// wrapper for SearchSelectize
		var searchControl = $('<div class="form-group my-1" id="search-control"></div>')
		searchControl.append($('<label class="control-label">Search a gene:</label>'))

		this.$el = $('<select id="search" class="form-control"></select>');
		searchControl.append(this.$el)
		$(this.container).append(searchControl)

		var callback = function(data){
			return data;
		}

		var self = this;
		this.$el.selectize({
			valueField: 'gene',
			labelField: 'gene',
			searchField: 'gene',
			sortField: 'gene',
			preload: 'focus',
			options: [],
			create:false,
			placeholder: 'gene symbol...',
			render: {
				option: function(item, escape){
					return '<ul class="list-unstyled">' + 
						'<li>' + escape(item.gene) + '</li>' +
						'<li>average expression:' + parseFloat(item.avg_expression).toFixed(1) + '</li>' +
						'</ul>';
				}
			},
			load: function(query, callback){
				if (!query.length) query = 'a'; // to preload some options when focused 
				$.ajax({
					url: self.synonymsUrl + '/' + encodeURIComponent(query),
					type: 'GET',
					dataType: 'json',
					error: function(){
						callback();
					},
					success: function(res){
						return callback(res);
					}
				});
			}
			});

		// on change, trigger('searched', query)
		this.$el[0].selectize.on('change', function(value){
			if (value !== ''){
				self.trigger('searched', value);
			}
		});
	},

});


var TermSearchSelectize = Backbone.View.extend({
	// selectize to search for genes by name
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		synonymsUrl: 'query_terms',
		optGroupUrl: '',
		retrieveUrl: 'get_terms'
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot highlightQuery once selectize is searched
		var retrieveUrl = this.retrieveUrl
		scatterPlot.listenTo(this, 'searched', function(query){
			scatterPlot.colorByScoresFromUrl(retrieveUrl, query);
		});

	},

	render: function(){
		// set up the DOMs
		// wrapper for SearchSelectize
		var searchControl = $('<div class="form-group" id="search-control"></div>')
		searchControl.append($('<label class="control-label">Text search: <i class="fas fa-info-circle" data-toggle="tooltip" title="Search a biological term such as a pathway and the viewer will overlay the enrichment scores of the searched term on the cells."></i></label>'))

		this.$el = $('<select id="search" class="form-control"></select>');
		searchControl.append(this.$el)
		$(this.container).append(searchControl)

		var callback = function(data){
			return data;
		}

		var self = this;
		// fetch optgroups from optGroupUrl
		$.getJSON(this.optGroupUrl, function(res){
			var optgroups = [];
			$.each(res, function(index, value){
				optgroups.push({$order: index+1, id: value['name'], name: value['name']});
			});

			self.$el.selectize({
				valueField: 'term',
				labelField: 'term',
				searchField: 'term',
				sortField: 'term',
				optgroupField: 'library',
				optgroupLabelField: 'name',
				optgroupValueField: 'id',
				lockOptgroupOrder: true,
				preload: false,
				options: [],
				placeholder: 'term...',
				optgroups: optgroups,
				create:false,
				render: {
					option: function(item, escape){
						var term = item.term.split('/')[0],
							type = item.term.split('/')[1];
						return '<ul class="list-unstyled">' + 
							'<li>' + escape(term) + '</li>' +
							'<li>' + escape(type) + '</li>' +
							'</ul>';
					}
				},
				load: function(query, callback){
					// if (!query.length) query = 'a'; // to preload some options when focused 
					if (query.length > 1){
						$.ajax({
							url: self.synonymsUrl + '/' + encodeURIComponent(query),
							type: 'GET',
							dataType: 'json',
							error: function(){
								callback();
							},
							success: function(res){
								return callback(res);
							}
						});
					}
				}
				});
			// on change, trigger('searched', query)
			self.$el[0].selectize.on('change', function(value){
				if (value !== ''){
					self.trigger('searched', value);
				}
			});
			// add tooltips
			$('[data-toggle="tooltip"]').tooltip({
				placement: 'auto',
				container: 'body',
			});
		});
	},
});

var LibSearchSelectize = Backbone.View.extend({
	// selectize to search for library by name
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		synonymsUrl: 'query_libs',
		retrieveUrl: 'get_lib',
		optionsShow: [],
		label: ''
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot highlightQuery once selectize is searched
		var retrieveUrl = this.retrieveUrl;
		scatterPlot.listenTo(this, 'searched', function(query){
			scatterPlot.colorByCategoriesFromUrl(retrieveUrl, query);
		});

	},

	_render: function(data){
		// set up the DOMs
		// wrapper for SearchSelectize
		var searchControl = $('<div class="form-group" id="search-control"></div>')
		searchControl.append($('<label class="control-label">' + this.label + '</label>'))

		this.$el = $('<select id="search" class="form-control selectpicker" title="Select a library..."></select>');
		
		data = _.groupBy(data, 'type');
		for (var type in data){
			var optgroup = $('<optgroup>').attr('label', type);
			for (var i = 0; i < data[type].length; i++) {
				var rec = data[type][i];
				var option = $('<option>').text(rec.name).attr('value', rec.name + '/'+ rec.type)
				optgroup.append(option)
			}
			this.$el.append(optgroup)
		}

		searchControl.append(this.$el)
		$(this.container).append(searchControl)

		this.$el.selectpicker({
			style: 'btn-outline-secondary btn-sm',
		});
		this.$el.selectpicker('refresh');

		// on change, trigger('searched', option)
		var self = this;
		this.$el.on('changed.bs.select', function (e, clickedIndex, isSelected, previousValue){
			var selectedValue = $(this).val();
			var name = selectedValue.split('/')[0],
				type = selectedValue.split('/')[1];
			self.trigger('searched', {type: type, name: name});
		})
	},

	render: function(){
		var self = this;
		$.getJSON(this.synonymsUrl, function(data){
			// check if there is any options from synonymsUrl
			if (data.length > 0){
				data = _.filter(data, function(rec){ return self.optionsShow.indexOf(rec.name) !== -1 })
				self._render(data)
			}
		});
	},
});

var BrushBtns = Backbone.View.extend({
	// The buttons to toggle the modal of the selected samples by d3 brush
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		modal_url: null,
		base_url: 'brush/'
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);
		
		var self = this;
		this.listenTo(this.scatterPlot, 'brushended', function(ids){
			self.brushended(ids)
		})
	},

	render: function(){
		this.createDOM()
		// show if not 3d
		if (this.scatterPlot.is3d){
			this.hide();
		}
	},

	createDOM: function(){
		// set up the btn-group div
		this.div = $('<div id="modal-btn" class="btn-group" role="group"></div>')
		// set up the modal button
		this.button = $('<a class="btn btn-outline-info">View Selected Samples Report</a>');
		var self = this;
		this.button.click(function(e){
			e.preventDefault();
			if (self.modal_url.startsWith('sample/')){
				window.location.href = self.modal_url;
			} else {
				$('#brush-modal').modal('show')
				if ($('.modal-body').is(':empty')){
					$(".modal-body").append($('<p id="wait-msg">please wait loading report...</p>'))
					// load content when modal-body is empty
					$(".modal-body").load(self.modal_url);
				}				
			}
		});

		// set up the clear btn
		this.clearBtn = $('<a class="btn btn-outline-secondary">Clear</a>');
		this.clearBtn.click(function(e){
			e.preventDefault();
			self.trigger('clearBrush');
			self.hide();
			self.scatterPlot.clearBrush();
		})

		this.hide()
		this.div.append(this.button)
		this.div.append(this.clearBtn)
		$(this.container).append(this.div);
	},

	show: function(){
		this.div.css('display', 'inherit')
	},

	hide: function(){
		this.div.css('display', 'none')
	},

	brushended: function(ids){
		// show the buttons and POST the sample_ids to the 
		// server to get the url for the modal.
		this.show();
		$('.modal-body').empty();
		if (ids.length === 1){ // only one cell is selected
			this.modal_url = 'sample/' + ids[0];
		} else {
			var self = this;
			$.ajax({
				method: 'POST',
				url: self.base_url,
				contentType: 'application/json',
				data: JSON.stringify({ids: ids}),
				dataType: 'json',
				success: function(resp_data){
					self.modal_url = self.base_url + '/' + resp_data.hash;
					// $(".modal-body").load(self.modal_url);
				}
			})			
		}
	},
});

var BrushModal = Backbone.View.extend({
	// Used for toggling the mouseEvents of the scatterPlot.
	defaults: {
		scatterPlot: Scatter3dView,
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;
		this.listenTo(this.model, 'sync', this.toggleScatterPlotMouseEvents);

	},

	toggleScatterPlotMouseEvents: function(){
		this.$el = $('#brush-modal');
		var scatterPlot = this.scatterPlot;
		this.$el.on('show.bs.modal', function(e){
			scatterPlot.removeMouseEvents()
		});
		this.$el.on('hide.bs.modal', function(e){
			scatterPlot.addMouseEvents()
		});
	},

});

var BrushController = Backbone.View.extend({
	// Used for enabling and disabling brush selection.
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;
		this.listenTo(this.model, 'sync', this.createDOM);
		this.listenTo(this.scatterPlot, 'modelChanged', this.render)
	},

	render: function(){
		if(this.scatterPlot.is3d){
			this.detach()
		}else{
			this.attach()
		}
	},

	createDOM: function(){
		this.button = $('<button id="brush-controler" class="btn btn-info btn-sm" data-toggle="button" aria-pressed="false"><i class="fas fa-crosshairs"></i> Free Selection (Lasso)</button>');
		this.button.click(function(e){
			e.preventDefault()
			if (self.sdv.shiftKey){
				self.sdv.disableBrush()
			} else {
				self.sdv.enableBrush()
			}
		});
		if (!this.scatterPlot.is3d){
			this.attach()
		}
	},

	depress: function(){
		this.button.attr('aria-pressed', 'false')
		this.button.removeClass('active')
	},

	attach: function(){
		$(this.container).append(this.button);
	},

	detach: function(){
		if (this.button){
			this.button.detach();
		}
	},
});


var Overlay = Backbone.View.extend({
	// An overlay to display current status.
	tagName: 'div',
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		
		this.render();
		this.changeMessage('Retrieving data from the server... please wait');

		// finished retrieving data
		var self = this;
		this.listenTo(this.scatterPlot.model, 'sync', function(){
			self.changeMessage('Data retrieved. Rendering scatter plot...');
		});
		// finished rendering
		this.listenTo(this.scatterPlot, 'shapeChanged',
			this.remove)
	},

	render: function(){
		var w = $(this.container).width() + 'px',
			h = $(this.container).height() + 'px';
		this.el = d3.select(this.container)
			.append(this.tagName)
			.style('width', w)
			.style('height', h)
			.style('z-index', 10)
			.style('position', 'absolute')
			.style('right', '0px')
			.style('top', '0px')
			.style('background-color', 'rgba(50, 50, 50, 0.2)')
			.style('cursor', 'wait');

		this.msgDiv = this.el.append('div')
			.style('z-index', 11)
			.style('position', 'absolute')
			.style('text-align', 'center')
			.style('width', '100%')
			.style('top', '50%')
			.style('font-size', '250%');
		
		return this;
	},

	changeMessage: function(msg){
		this.msgDiv.text(msg);
	},

	remove: function(){
		this.changeMessage('Rendering completed')
		// COMPLETELY UNBIND THE VIEW
		this.undelegateEvents();
		// Remove view from DOM
		this.el.remove()
		// this.remove();  
		// Backbone.View.prototype.remove.call(this);
	},
});


function replaceDimInUrl(url, n_dim){
	var sl = url.split('/').slice(0, 3)
	sl.push(n_dim)
	return sl.join('/')
}

var DimToggle = Backbone.View.extend({
	// toggling between 2/3 dim
	tagName: 'input',
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		graphs: [], // an array of objects specifying the available visualizations
		defaultColorKey: undefined,
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		
		this.listenTo(this.scatterPlot.model, 'sync', this.render);
		// responsively disable button if the n_dim is not available
		var graphs = _.indexBy(this.graphs, 'name');
		var self = this;
		this.listenTo(this.scatterPlot, 'modelChanged', function(url){
			var visualization = url.split('/')[2]
			if (!graphs[visualization].has3d){
				self.disable();
			} else {
				self.enable();
			}
		});

	},
	
	render: function(){
		this.$el = $('<' + this.tagName + '>').attr('type', 'checkbox')
			.attr('id', 'dim-toggle')
			.attr('data-toggle', 'toggle')
			.attr('data-onstyle', 'success')
			.attr('data-offstyle', 'info')
			.attr('data-on', '3D')
			.attr('data-off', '2D')

		$(this.container).append(this.$el)

		var sdv = this.scatterPlot;
		// switch to the current n_dim based on scatterPlot
		var n_dim = sdv.is3d ? 3 : 2;
		this.switchTo(n_dim);
		
		var defaultColorKey = this.defaultColorKey;
		// when this is switched
		this.$el.change(function(){
			var currentModelUrl = sdv.model.url();
			if ($(this).prop('checked')) {
				var newUrl = replaceDimInUrl(currentModelUrl, '3')
			} else {
				var newUrl = replaceDimInUrl(currentModelUrl, '2')
			}

			if (newUrl !== currentModelUrl){
				sdv.colorKey = defaultColorKey;
				sdv.changeModel(newUrl)
			}
		});
	},

	disable: function(){
		this.$el.parent().addClass('disabled')
		this.$el.bootstrapToggle('disable')
	},

	enable: function(){
		this.$el.parent().removeClass('disabled')
		this.$el.bootstrapToggle('enable')
	},

	switchTo: function(n_dim){
		if (n_dim === 3){
			this.$el.bootstrapToggle('on')
		} else {
			this.$el.bootstrapToggle('off')
		}
	},
})

var VisualizationBtnGroup = Backbone.View.extend({
	// the button group to toggle amond different visualizations
	tagName: 'div',
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		graphs: [], // an array of objects specifying the available visualizations
		defaultColorKey: undefined,
	},
	
	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)
		
		this.listenTo(this.scatterPlot.model, 'sync', this.render);
	},
	
	render: function(){
		this.$el = $('<' + this.tagName + '>').attr('class', 'btn-group btn-group-toggle')
			.attr('data-toggle', 'buttons')

		for (var i = this.graphs.length - 1; i >= 0; i--) {
			var rec = this.graphs[i];
			var btn = $('<label>')
				.attr('class', 'btn btn-info')
				.attr('id', rec.name)
				.text(rec.name)
			var radio = $('<input>').attr('type', 'radio')
				.attr('name', 'options')
				.attr('autocomplete', 'off')
				.attr('value', rec.name)
				
			btn.append(radio)
			this.$el.append(btn)
		}

		var sdv = this.scatterPlot;
		var currentModelUrl = sdv.model.url();
		var graph_info = _.indexBy(this.graphs, 'name')

		// switch to the current visualization
		this.switchTo(currentModelUrl.split('/')[2])

		var defaultColorKey = this.defaultColorKey;
		// handle on change event to make sdv change its model
		$('input:radio[name=options]', this.$el).change(function() {
			// get the new url based on the selection
			currentModelUrl = sdv.model.url();
			var sl = currentModelUrl.split('/')
			var currentDim = parseInt(sl[3])
			if (currentDim === 3 && !graph_info[this.value].has3d){
				// currently display 3d, but the next graph has no 3d available
				sl[3] = '2';
			}
			sl[2] = this.value;
			var newUrl = sl.join('/');
			sdv.colorKey = defaultColorKey;
			sdv.changeModel(newUrl)
		});
		// put on
		$(this.container).append(this.$el)
	},

	switchTo: function(name){
		// switch the button in the button group to active
		$('label', this.$el).removeClass('active');
		$("#"+name, this.$el).addClass('active');
	},

})
