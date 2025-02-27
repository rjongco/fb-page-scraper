/*
	Photon by HTML5 UP
	html5up.net | @ajlkn
	Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

	var	$window = $(window),
		$body = $('body');

	// Breakpoints.
		breakpoints({
			xlarge:   [ '1141px',  '1680px' ],
			large:    [ '981px',   '1140px' ],
			medium:   [ '737px',   '980px'  ],
			small:    [ '481px',   '736px'  ],
			xsmall:   [ '321px',   '480px'  ],
			xxsmall:  [ null,      '320px'  ]
		});

	// Play initial animations on page load.
		$window.on('load', function() {
			window.setTimeout(function() {
				$body.removeClass('is-preload');
			}, 100);
		});

	// Scrolly.
		$('.scrolly').scrolly();

})(jQuery);

function jsonToCsv(json) {
	const header = Object.keys(json[0]);
	const rows = json.map(row => 
	  header.map(fieldName => JSON.stringify(row[fieldName], (key, value) => value ?? '')).join(',')
	);
	return [header.join(','), ...rows].join('\n');
}

$(document).ready(function() {
	$("input#fb_url").val('');
	const downloadLink = document.getElementById('main-download');
	$(downloadLink).hide()

	let wait = $('div[data-id="wait"]').attr('data-value') ?? 0
	$('div[data-id="wait"]').remove()
	let status = $('div[data-id="status"]').attr('data-value') ?? 0
	$('div[data-id="status"]').remove()

	const progress = new ldBar("#main-loader")
	if(status == 'standby'){
		$('#main-logs').text('Click on "Start Scraping" to start collecting FB posts from the URL.')
	} else if(status == 'cooldown') {
		$('#main-logs').text('You can comeback later.')
	}
	var scrape = $("button#scrape")
	var socket = io.connect('http://127.0.0.1:5000');
	scrape.click(async function() {
		try{
			if(wait > 0) return false;
			var fbpageurl = $("input#fb_url").val().trim();  // Get the input value
			var log_code = null

			const response = await fetch('/scrape',{
				method: 'post',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					url: fbpageurl
				})
			})
			const data = await response.json();
			let message = data.message
			let hash = data.hash
			if(!!!hash){
				throw new Error(message)
			}
			
			
			socket.emit('scrape', {hash: hash})
		
			socket.on('error', function(msg) {
				console.log(msg)
				throw new error(msg)
			});
			socket.on('stream', function(data, acknowledgement) {
				acknowledgement(true)
				let percentage = Math.floor(data.percent)
				$('#main-logs').text(`${data.log} ${percentage}%`)
				progress.set(parseInt(percentage))

				if (data.completion == true){
					progress.set(100, false)
					$('#main-loader').fadeOut(1000)
					var collected_data = data.data
					const csv = jsonToCsv(collected_data);
					downloadLink.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
					downloadLink.target = '_blank';
					downloadLink.download = 'data.csv'; // Set the filename
					$(downloadLink).fadeIn(1000)
				}
				
			});
		}catch(error){
			console.log('err catch',error)
			alert(error);
		}
	});

})
