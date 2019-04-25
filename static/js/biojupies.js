// Utils functions for handling the generation of biojupies notebooks

function goBack() {
    window.history.back();
}

// Preview Table
function addPreviewTable(response, metadata, previewSelector) {

	// Define table
	var $table = $('<table>', {'class': 'table table-sm table-hover table-striped w-100'}).append($('<thead>').append($('<tr>', {'class': 'very-small text-center border-grey border-left-0 border-right-0'}))).append($('<tbody>'));

	// Add headers
	label = metadata ? 'Gene' : 'Sample'
	$table.find('tr').append($('<th>', {'class': 'text-nowrap'}).html(label));
	$.each(response['columns'], function(i, col) {
		$table.find('tr').append($('<th>', {'class': 'text-nowrap'}).html(col));
	})

	// Get row number
	n = metadata ? 6 : response['index'].length

	// Add rows
	for (i=0; i<n; i++) {
		var $tr = $('<tr>').append($('<td>', {'class': 'font-weight-bold text-center text-nowrap'}).html(response['index'][i]));
		$.each(response['data'][i], function(i, val) {
			$tr.append($('<td>', {'class': 'font-weight-light text-center tiny'}).html(val));
		})
		$table.find('tbody').append($tr);
	}

    // Remove spinner
    var spinnerSelector = previewSelector + " > div.spinner-border";
    $(spinnerSelector).addClass('d-none');
    // Add table
    var $tableWrapper = $('<div>', {'class': 'table-wrapper'})
    $tableWrapper.append($table)
	$(previewSelector).append($tableWrapper).removeClass('d-none').addClass('preview');
}


function generateNotebook (upload_id){
    // This function sends POST request to notebook generator server
    // update notebook status
    var spinner = $('<div>').attr('class', 'spinner-border text-secondary')
        .attr('role', 'status')
        .attr('id', 'spinner');
    spinner.append($('<span>').attr('class', 'sr-only').text('Loading...'))

    $('#notebook-status').css('display', 'block').text('Generating notebook...')
        .append(spinner);

    var notebook_config = {
        notebook: {
            title: 'Example Notebook for user data',
            live: 'False',
            version: 'v1.0.5'
        },
        tools: [
            {
            tool_string: "pca",
            parameters: {
            nr_genes: "500",
            normalization: "CPM",
            z_score: "True",
            plot_type: "interactive"
            }
        },
        {
            tool_string: "pca",
            parameters: {
            nr_genes: "500",
            normalization: "magic",
            z_score: "True",
            plot_type: "interactive"
            }
        },      
        {
            tool_string: "clustering",
            parameters: {
            nr_genes: "500",
            normalization: "logCPM",
            plot_type: "interactive"
            }
        },
        {
            tool_string: "monocle",
            parameters: {
            color_by: "Pseudotime",
            plot_type: "interactive"
            }
        },
        {
            tool_string: "library_size_analysis",
            parameters: {
            plot_type: "interactive"
            }
        }
        ],
        data: {
            source: 'upload',
            parameters: {
                uid: upload_id
            }
        },
        signature: {},
        terms: []
    };

    var NOTEBOOK_GENERATOR_URL = 'http://amp.pharm.mssm.edu/notebook-generator-server-sc/api/generate';
    // post notebook_config to server to generate notebook
    $.ajax({
        type: 'post',
        url: NOTEBOOK_GENERATOR_URL,
        data: JSON.stringify(notebook_config),
        dataType: 'json',
        contentType: 'application/json',
        success: function(resp){
            console.log(resp)
            // remove spinner
            $('#spinner').remove();
            var linkToNotebook = $('<a>').attr('href', resp.nbviewer_url)
                .attr('target', '_blank')
                .text(resp.notebook_uid);
            $('#notebook-status').text('Notebook generated successfully and can be access via this link: ')
            $('#notebook-status').append(linkToNotebook);
        },
        error: function(e){
            console.log(e)
            $('#spinner').remove();
            $('#notebook-status').append('Sorry, there has been an error.');
        }
    });

}
