var colors10 = _.map(_.range(10), d3.scale.category10());
  
// Parse data for gene expression bar plot
var genes = _.pluck(sample_data.genes, 'gene');
var gene_series_base = {
  cursor: 'pointer',
  point: {
    events: {
      click: function(){
        location.href = 'http://amp.pharm.mssm.edu/Harmonizome/gene/' + 
        this.options.gene.toUpperCase();    
      }
    }
  },
}

var gene_data_z = _.map(sample_data.genes, function(d){
  var val = d.val
  var color = colors10[0];
  if (val > 0){
    var color = colors10[3]
  }
  return {
    gene: d.gene,
    y: parseFloat(d.val.toFixed(3)),
    color: color
  };
});

var gene_series_z = Object.assign(
  {name: 'z-scores', data: gene_data_z},
  gene_series_base
  );

// var gene_data_cpm = _.map(sample_data.genes, function(d){
//   var val = d.val
//   var color = colors10[0];
//   if (val > 0){
//     var color = colors10[3]
//   }
//   return {
//     gene: d.gene,
//     y: parseFloat(d.cpm.toFixed(2)),
//     color: color
//   };
// });

// var gene_series_cpm = Object.assign( 
//   {name: 'CPM', data: gene_data_cpm},
//   gene_series_base
//   );


var chart = new Highcharts.chart('gene-chart', {
  chart: {
    type: 'bar'
  },
  title: {
    text: 'Relative expression'
  },
  xAxis: {
    categories: genes,
    labels: {
      step: 1  
    }
  },
  yAxis: {
    title: {text: 'z-score'}
  },
  credits: {
    enabled: false
  },
  series: []
});
chart.addSeries(gene_series_z)

// $("#gene-btn").click(function(){
//   var currentAttr = chart.yAxis[0].axisTitle.textStr;
//   if (currentAttr == 'z-score'){ // switch to CPM
//     chart.series[0].remove(false)
//     chart.addSeries(gene_series_cpm, false)
//     chart.setTitle({text: 'Absolute expression'}, false)
//     chart.yAxis[0].setTitle({text:'CPM'}, true);
//   }else{
//     chart.series[0].remove(false)
//     chart.addSeries(gene_series_z, false)
//     chart.setTitle({text: 'Relative expression'}, false)
//     chart.yAxis[0].setTitle({text:'z-score'}, true);
//   }
// })


function makeAndManageSelectBarChart(selectSelector, chartSelector, title, scoreName, data){
  // init and handling select events for bar charts given data

  // Parse data for Enrichment bar plot
  var gene_set_libs = _.keys(data);

  // add options in <select>
  for (var i = gene_set_libs.length - 1; i >= 0; i--) {
    var lib = gene_set_libs[i];
    $(selectSelector).append($('<option>'+ lib +'</option>'));
  }

  // helper function to get the series for enrichr
  var get_lib_data = function(lib){
    var enrichData = _.map(data[lib], function(d){
      return {
        term: d.term,
        y: parseFloat(d.score.toFixed(3)),
        color: colors10[3]
      };
    });
    var enrich_series = {name: scoreName, data: enrichData}
    return enrich_series
  }

  var default_lib = gene_set_libs.slice(-1)
  var enrich_series = get_lib_data(default_lib)

  var chart2 = new Highcharts.chart(chartSelector, {
    chart: {
      type: 'bar'
    },
    plotOptions: {
      series: {
        pointWidth: 30,
      }
    },
    title: {
      text: title + default_lib
    },
    xAxis: {
      categories: _.pluck(enrich_series.data, 'term'),
      labels: {
        step: 1,
        overflow: 'justify',
        align: 'left',
        x: 5,
        reserveSpace: false,
        style: {
          color: colors10[9],
          fontWeight: 'bold',
          fontSize: '14px',
          whiteSpace: 'nowrap'
        }
      }
    },
    yAxis: {
      title: {text: scoreName}
    },
    credits: {
      enabled: false
    },
    series: []
  });
  chart2.addSeries(enrich_series)

  $(selectSelector).on('changed.bs.select', function(){
    var selected_lib = $(this).val();
    var selected_series = get_lib_data(selected_lib);
    chart2.series[0].remove(false)
    chart2.xAxis[0].setCategories(_.pluck(selected_series.data, 'term'), false)
    chart2.setTitle({text: title + selected_lib}, false)
    chart2.addSeries(selected_series, true)
  })
}

makeAndManageSelectBarChart('#enrichr-select', 
  'enrichr-chart',
  'Top enriched terms in ',
  'combined score',
  sample_data.enrichment
  );

makeAndManageSelectBarChart('#predict-select', 
  'predict-chart',
  'Most probable predictions from ',
  'probability',
  sample_data.prediction
  );


