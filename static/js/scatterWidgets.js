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
			.attr("transform", "translate(0, 0)");
		this.g.append('g')
			.attr('id', 'legendShape')
			.attr("class", "legendPanel")
			.attr("transform", "translate(0, 0)");

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

		var self = this
		// a hack here because d3.legend has no callback
		setTimeout(function(){self.moveShapeLegend();}, 500)

		return this;
	},
	
	moveShapeLegend: function(){
		var bbox = this.g.select('#legendColor')
			.node()
			.getBBox();
		// move legendShape accordingly
		console.log(bbox.height)
		var dy = bbox.height + 10;
		this.g.select('#legendShape')
			.transition()
			.attr('transform', 'translate(0, ' + dy + ')')
			.duration(500)
	}

});

// This is a map for the tooltips displayed to explain the 
// colorBy and shapeBy options.
var tooltipTexts = { 
	// 'p-value': 'An empirical p-value measuring the consistency between drug treatment replicates used for calculating the drug-induced signature.',
	// 'Scores': 'Similarity score measuring the overlap between the input DE genes and the signature DE genes divided by the effective input. The range of the score is [-1, 1]. Positive scores indicate similar signature whereas negative scores indicate opposite signature.',
	// 'Cell': 'Cell line for the drug perturbation',
	// 'Dose': 'Concentration of the drug',
	// 'Perturbation_ID': 'ID of the drug/small molecule compound',
	// 'Time': 'Duration of drug treatment',
	// 'Perturbation': 'Name of drug/small molecule compound',
	// 'EHR_Coprescribed_Drugs': 'Most frequently associated co-prescribed drug',
	// 'EHR_Diagnoses': 'Most frequently associated diagnosis',
	// 'Phase': 'Drug development phase',
	// 'MOA': 'Mechanisms of action',
	// 'Batch': 'Experimental batch',
	// 'DBSCAN-clustering': 'Signature clustering result using DBSCAN algorithm',
	// 'KMeans-clustering': 'Signature clustering result using KMeans algorithm',
	// 'rings': "The molecule's rings in the drug/compounds",
	// 'scaffolds': "The chemical scaffolds of the drugs/compounds",
	// 'n_rings': 'Number of rings in the drugs/compounds',
	// 'n_scaffolds': 'Number of scaffolds in the drugs/compounds',
	// 'predicted_MOA': 'Mechanisms of action predicted based on gene expression and chemical signatures',
};

var Controler = Backbone.View.extend({

	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		w: 300,
		h: 800,
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

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

	},

	render: function(){
		// set up DOMs for the controler
		this.el = d3.select(this.container)
			.append('div')
			.attr('id', 'controls')
			.style('width', this.w)
			.style('height', this.h);

		var model = this.model;
		// filter out metas used as index
		var metas = _.filter(model.metas, function(meta){ return meta.nUnique < model.n; });
		var self = this;
		// filter out metas not suitable for shapes
		var metasShape = _.filter(metas, function(meta){ return meta.nUnique < 7 });
		// Only retrain these attributes as shapes
		// var metasShapeNames = ['p-value', 'Dose', 'Time'];
		// var metasShape = _.filter(metas, function(meta){return metasShapeNames.indexOf(meta.name) !== -1 });
		if (metasShape.length > 0){
			// Shapes: 
			var shapeControl = this.el.append('div')
				.attr('class', 'form-group my-1');
			shapeControl.append('label')
				.attr('class', 'control-label')
				.text('Shape by:');

			var shapeSelect = shapeControl.append('select')
				.attr('id', 'shape')
				.attr('class', 'form-control selectpicker')
				.on('change', function(){
					var selectedMetaKey = d3.select('#shape').property('value');
					self.trigger('shapeChanged', selectedMetaKey)
				});

			var shapeOptions = shapeSelect
				.selectAll('option')
				.data(_.pluck(metasShape, 'name')).enter()
				.append('option')
				.text(function(d){return d;})
				.attr('value', function(d){return d;})
				.attr('data-content', function(d){
					if (tooltipTexts.hasOwnProperty(d)) {
						return '<div title="'+tooltipTexts[d]+
							'" data-toggle="tooltip">'+d+'</div>';
					};
				});
		}

		// Colors
		var colorControl = this.el.append('div')
			.attr('class', 'form-group my-1')
		colorControl.append('label')
			.attr('class', 'control-label')
			.text('Color by:');

		var colorSelect = colorControl.append('select')
			.attr('id', 'color')
			.attr('class', 'form-control selectpicker')
			.on('change', function(){
				var selectedMetaKey = d3.select('#color').property('value');
				self.trigger('colorChanged', selectedMetaKey)
			});

		var metasColorExclude = ['p-value', 'Dose', 'Perturbation_ID'];
		var metasColor = _.filter(metas, function(meta){return metasColorExclude.indexOf(meta.name) === -1 });
		var colorOptions = colorSelect
			.selectAll('option')
			.data(_.pluck(metasColor, 'name')).enter()
			.append('option')
			.text(function(d){return d;})
			.attr('value', function(d){return d;})
			.attr('data-content', function(d){
				if (tooltipTexts.hasOwnProperty(d)) {
					if (d==='Perturbation') {
					return '<div title="'+tooltipTexts[d]+
						'" data-toggle="tooltip">Popular-Perturbation</div>'; 
					}else {
						return '<div title="'+tooltipTexts[d]+
							'" data-toggle="tooltip">'+d+'</div>';						
					}

				} else{
					return '<div>' + d + '</div>';
				};
			});

		$('.selectpicker').selectpicker({
			style: 'btn-outline-secondary btn-sm',
		});

		$('.selectpicker').on('shown.bs.select', function(e){
			// $('[data-toggle="tooltip"]').tooltip({
			// 	placement: 'auto',
			// 	container: 'body',
			// });			
		})

		return this;
	},

	changeSelection: function(){
		// change the current selected option to value
		$('#shape').val(this.scatterPlot.shapeKey); 
		$('#color').val(this.scatterPlot.colorKey);
	},

});

var SearchSelectize = Backbone.View.extend({
	// selectize to search for genes by name
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		synonymsUrl: 'query_genes',
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot highlightQuery once selectize is searched
		scatterPlot.listenTo(this, 'searched', function(query){
			scatterPlot.colorByGeneExpression(query);
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
			placeholder: 'Type the symbol of a gene',
			render: {
				option: function(item, escape){
					return '<ul class="list-unstyled">' + 
						'<li>' + escape(item.gene) + '</li>' +
						'<li>average expression:' + parseFloat(item.avg_expression).toFixed(1) + '</li>' +
						'</ul>';
				}
			},
			load: function(query, callback){
				if (!query.length) query = 'co'; // to preload some options when focused 
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
		optGroupUrl: ''
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot highlightQuery once selectize is searched
		scatterPlot.listenTo(this, 'searched', function(query){
			scatterPlot.colorByTermScores(query);
		});

	},

	render: function(){
		// set up the DOMs
		// wrapper for SearchSelectize
		var searchControl = $('<div class="form-group" id="search-control"></div>')
		searchControl.append($('<label class="control-label">Search a term: <i class="fas fa-info-circle" data-toggle="tooltip" title="Search a biological term such as a pathway and the viewer will overlay the enrichment scores of the searched term on the cells."></i></label>'))

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
				preload: 'focus',
				options: [],
				placeholder: 'e.g. ABC transporters',
				optgroups: optgroups,
				create:false,
				render: {
					option: function(item, escape){
						return '<ul class="list-unstyled">' + 
							'<li>' + escape(item.term) + '</li>' +
							'</ul>';
					}
				},
				load: function(query, callback){
					if (!query.length) query = 'co'; // to preload some options when focused 
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
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot highlightQuery once selectize is searched
		scatterPlot.listenTo(this, 'searched', function(query){
			scatterPlot.colorByGeneSetLibrary(query);
		});

	},

	render: function(){
		// set up the DOMs
		// wrapper for SearchSelectize
		var searchControl = $('<div class="form-group" id="search-control"></div>')
		searchControl.append($('<label class="control-label">Search a gene-set library:</label>'))

		this.$el = $('<select id="search" class="form-control"></select>');
		searchControl.append(this.$el)
		$(this.container).append(searchControl)

		var callback = function(data){
			return data;
		}

		var self = this;
		this.$el.selectize({
			valueField: 'name',
			labelField: 'name',
			searchField: 'name',
			sortField: 'name',
			preload: 'focus',
			options: [],
			create:false,
			placeholder: 'Type a gene-set library',
			render: {
				option: function(item, escape){
					return '<ul class="list-unstyled">' + 
						'<li>' + escape(item.name) + '</li>' +
						'</ul>';
				}
			},
			load: function(query, callback){
				$.ajax({
					url: self.synonymsUrl,
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

var SigSimSearch = Backbone.View.extend({
	// The frontend for signature similarity search
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		exampleGenes: {
			up: ["ZNF238","ACACA","ACAT2","ACLY","ACSL3","C10ORF10","C14ORF1","CCL2","CCNG2","CD46","CDKN1A","CETN2","CLIC4","CYB5A","CYP1B1","CYP51A1","DBI","DDIT4","DHCR24","DHCR7","DSC3","DSG3","EBP","EFNA1","ELOVL5","ELOVL6","FABP7","FADS1","FADS2","FDFT1","FDPS","FGFBP1","FN1","GLUL","HMGCR","HMGCS1","HOPX","HS3ST2","HSD17B7","IDI1","IL32","INSIG1","IRS2","KHDRBS3","KRT14","KRT15","KRT6B","LDLR","LPIN1","LSS","MAP7","ME1","MSMO1","MTSS1","NFKBIA","NOV","NPC1","NSDHL","PANK3","PGD","PLA2G2A","PNRC1","PPL","PRKCH","PSAP","RDH11","SC5DL","SCD","SCEL","SDPR","SEPP1","SLC2A6","SLC31A2","SLC39A6","SMPDL3A","SNCA","SPRR1B","SQLE","SREBF1","SREBF2","STXBP1","TM7SF2","TNFAIP3","VGLL4","ZFAND5","ZNF185"],
			down:["ARMCX2","BST2","CA2","F12","GDF15","GPX7","IFI6","IGFBP7","KCNJ16","KRT7","MDK","NID2","NOP56","NR2F6","PDGFRA","PROM1","RRP8","SAMSN1","SCG5","SERPINE2","SLC4A4","TRIP6"]
		}, 
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

		var scatterPlot = this.scatterPlot;
		// scatterPlot colorByScores once the similarity search result is returned
		scatterPlot.listenTo(this, 'searchResultGot', function(scores){
			scatterPlot.colorByScores(scores);
		});
	},

	render: function(){
		// set up DOMs
		var container = $(this.container);
		container.append($('<h4>Signature Similarity Search:</h4>'))
		var upGeneDiv = $('<div class="form-group">')
		upGeneDiv.append($('<label for="upGenes" class="control-label">Up genes</label>'));
		upGeneDiv.append($('<textarea name="upGenes" rows="5" class="form-control" required></textarea>'));

		var dnGeneDiv = $('<div class="form-group">')
		dnGeneDiv.append($('<label for="dnGenes" class="control-label">Down genes</label>'));
		dnGeneDiv.append($('<textarea name="dnGenes" rows="5" class="form-control" required></textarea>'));

		var self = this;
		var exampleBtn = $('<button class="btn btn pull-left">Example</button>').click(function(e){
			$('[name="dnGenes"]').val(self.exampleGenes.down.join('\n'));
			$('[name="upGenes"]').val(self.exampleGenes.up.join('\n'));
		});

		var submitBtn = $('<button class="btn btn pull-right">Submit</button>').click(function(e){
			self.doRequest();
		})

		// append everything to container
		container.append(upGeneDiv)
		container.append(dnGeneDiv)
		container.append(exampleBtn)
		container.append(submitBtn)

	},

	doRequest: function(){
		var self = this;
		var upGenes = $('[name="upGenes"]').val().split('\n');
		var dnGenes = $('[name="dnGenes"]').val().split('\n');
		// POST json to /search endpoint
		$.ajax('search', {
			data: JSON.stringify({up_genes: upGenes, down_genes: dnGenes}),
			contentType: 'application/json',
			type: 'POST',
			success: function(data){
				self.trigger('searchResultGot', data);
			}
		});		
	},
});


var SigSimSearchForm = Backbone.View.extend({
	// The <form> version of signature similarity search
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		exampleGenes: {
			up: ["ZNF238","ACACA","ACAT2","ACLY","ACSL3","C10ORF10","C14ORF1","CCL2","CCNG2","CD46","CDKN1A","CETN2","CLIC4","CYB5A","CYP1B1","CYP51A1","DBI","DDIT4","DHCR24","DHCR7","DSC3","DSG3","EBP","EFNA1","ELOVL5","ELOVL6","FABP7","FADS1","FADS2","FDFT1","FDPS","FGFBP1","FN1","GLUL","HMGCR","HMGCS1","HOPX","HS3ST2","HSD17B7","IDI1","IL32","INSIG1","IRS2","KHDRBS3","KRT14","KRT15","KRT6B","LDLR","LPIN1","LSS","MAP7","ME1","MSMO1","MTSS1","NFKBIA","NOV","NPC1","NSDHL","PANK3","PGD","PLA2G2A","PNRC1","PPL","PRKCH","PSAP","RDH11","SC5DL","SCD","SCEL","SDPR","SEPP1","SLC2A6","SLC31A2","SLC39A6","SMPDL3A","SNCA","SPRR1B","SQLE","SREBF1","SREBF2","STXBP1","TM7SF2","TNFAIP3","VGLL4","ZFAND5","ZNF185"],
			down:["ARMCX2","BST2","CA2","F12","GDF15","GPX7","IFI6","IGFBP7","KCNJ16","KRT7","MDK","NID2","NOP56","NR2F6","PDGFRA","PROM1","RRP8","SAMSN1","SCG5","SERPINE2","SLC4A4","TRIP6"]
		}, 
		action: 'search',
		result_id: undefined
	},

	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);
	},

	render: function(){
		// set up DOMs
		var form = $('<form method="post" id="geneSet"></form>');
		form.attr('action', this.action);

		form.append($('<h4>Signature Similarity Search:</h4>'))
		var upGeneDiv = $('<div class="form-group">')
		upGeneDiv.append($('<label for="upGenes" class="control-label">Up genes</label>'));
		this.upGeneTa = $('<textarea name="upGenes" rows="5" class="form-control" required></textarea>');
		upGeneDiv.append(this.upGeneTa);

		var dnGeneDiv = $('<div class="form-group">')
		dnGeneDiv.append($('<label for="dnGenes" class="control-label">Down genes</label>'));
		this.dnGeneTa = $('<textarea name="dnGenes" rows="5" class="form-control" required></textarea>');
		dnGeneDiv.append(this.dnGeneTa);

		var self = this;
		var exampleBtn = $('<button class="btn btn-default btn-xs pull-left">Example</button>').click(function(e){
			e.preventDefault();
			self.populateGenes(self.exampleGenes.up, self.exampleGenes.down);
		});

		var clearBtn = $('<button id="clear-btn" class="btn btn-default btn-xs">Clear</button>').click(function(e){
			e.preventDefault();
			self.populateGenes([], []);
		});

		var submitBtn = $('<input type="submit" class="btn btn-default btn-xs pull-right" value="Submit"></input>');

		var creedsDiv = $('<div class="form-group">');
		creedsDiv.append($('<label for="creeds-search" class="control-label">Fetch a siganture from <a href="http://amp.pharm.mssm.edu/CREEDS/" target="_blank">CREEDS</a></label>'));
		var creedsSelectize = $('<select name="creeds-search" id="creeds-search" class="form-control"></select>');
		creedsDiv.append(creedsSelectize)


		// append everything to form
		form.append(upGeneDiv)
		form.append(dnGeneDiv)
		form.append(creedsDiv)
		form.append(exampleBtn)
		form.append(clearBtn)
		form.append(submitBtn)
		
		// append form the container
		$(this.container).append(form)
		// populate input genes if result_id is defined
		if (this.result_id){
			this.populateInputGenes();
		}

		// creedsSelectize
		var callback = function(data){
			return data;
		}

		creedsSelectize.selectize({
			valueField: 'id',
			labelField: 'name',
			searchField: 'name',
			sortField: 'name',
			optgroupField: 'type',
			optgroupLabelField: 'name',
			optgroupValueField: 'id',
			lockOptgroupOrder: true,
			preload: 'focus',
			options: [],
			placeholder: 'e.g. diabetes',
			optgroups: [
				{$order: 3, id: 'gene', name: 'gene'},
				{$order: 2, id: 'drug', name: 'drug'},
				{$order: 1, id: 'disease', name: 'disease'}
				],
			create:false,
			render: {
				option: function(item, escape){
					return '<ul class="list-unstyled">' + 
						'<li>' + escape(item.name) + '</li>' +
						'<li>GEO ID:' + escape(item.geo_id) + '</li>' +
						'<li>CREEDS ID:' + escape(item.id) + '</li>' +
						'<li>organism:' + escape(item.organism) + '</li>' +
						'</ul>';
				},
				item: function(item, escape){
					return '<div>' + 
						'<span class="sig-name">' + escape(item.name) + '</span>' + 
						'<span class="sig-meta"> (' + escape(item.geo_id) + ', ' + 
						escape(item.organism) + ')</span>' + 
						'</div>';
				},

			},
			load: function(query, callback){
				if (!query.length) query = 'c';
				$.ajax({
					url: 'CREEDS/search/' + encodeURIComponent(query),
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

		creedsSelectize[0].selectize.on('change', function(creeds_id){
			self.populateCreedsGenes(creeds_id)
		})


	},

	populateGenes: function(upGenes, dnGenes){
		// To populate <textarea> with up/down genes
		this.upGeneTa.val(upGenes.join('\n'));
		this.dnGeneTa.val(dnGenes.join('\n'))
	},

	populateInputGenes: function(result_id){
		// Populate <textarea> with input up/down genes retrieved from the DB
		var self = this;
		$.getJSON('result/genes/'+this.result_id, function(geneSet){
			self.populateGenes(geneSet.upGenes, geneSet.dnGenes);
		});
	},

	populateCreedsGenes: function(creeds_id){
		// To populate <textarea> with CREEDS genes
		var self = this;
		$.getJSON('CREEDS/genes/' + creeds_id, function(geneSet){
			self.populateGenes(geneSet.upGenes, geneSet.dnGenes)
		});
	},
});

var ResultModalBtn = Backbone.View.extend({
	// The button to toggle the modal of similarity search result
	defaults: {
		container: document.body,
		scatterPlot: Scatter3dView,
		result_id: undefined
	},
	
	initialize: function(options){
		if (options === undefined) {options = {}}
		_.defaults(options, this.defaults)
		_.defaults(this, options)

		this.model = this.scatterPlot.model;

		this.listenTo(this.model, 'sync', this.render);

	},

	render: function(){
		// set up the button
		this.button = $('<a id="modal-btn" class="btn btn-info">Show detailed results</a>');
		var modal_url = 'result/modal/' + this.result_id;

		this.button.click(function(e){
			e.preventDefault();
			$('#result-modal').modal('show')
			$(".modal-body").load(modal_url);
		});
		$(this.container).append(this.button);
	},

});

var ResultModal = Backbone.View.extend({
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
		this.$el = $('#result-modal');
		var scatterPlot = this.scatterPlot;
		this.$el.on('show.bs.modal', function(e){
			scatterPlot.removeMouseEvents()
		});
		this.$el.on('hide.bs.modal', function(e){
			scatterPlot.addMouseEvents()
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
		// set up the btn-group div
		this.div = $('<div id="modal-btn" class="btn-group" role="group"></div>')
		// set up the modal button
		this.button = $('<a class="btn btn-outline-info">View Selected Samples Report</a>');
		var self = this;

		this.button.click(function(e){
			e.preventDefault();
			$('#brush-modal').modal('show')
			if ($('.modal-body').is(':empty')){
				// load content when modal-body is empty
				$(".modal-body").load(self.modal_url);
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
		this.listenTo(this.model, 'sync', this.render);
	},

	render: function(){
		this.button = $('<button class="btn btn-info btn-sm" data-toggle="button" aria-pressed="false"><i class="fas fa-crosshairs"></i> Free Selection (Lasso)</button>');
		this.button.click(function(e){
			e.preventDefault()
			if (self.sdv.shiftKey){
				self.sdv.disableBrush()
			} else {
				self.sdv.enableBrush()
			}
		});
		$(this.container).append(this.button);
	},

	depress: function(){
		this.button.attr('aria-pressed', 'false')
		this.button.removeClass('active')
	}

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

