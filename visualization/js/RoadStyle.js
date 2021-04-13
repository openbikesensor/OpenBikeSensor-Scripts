class RoadStyle{
	constructor(){
		this.defaultStyle = new ol.style.Style({
			stroke: new ol.style.Stroke({
				color: [0, 0, 0, 255],
				width: 2,
			})
		});

	}

	initialize(){
	}

	select(){
	}

	deselect(){
	}

	styleFunction(feature, resolution, selected=false, hovered=false){
		return this.defaultStyle;
	}
}



class RoadStyle_MeanDistance extends RoadStyle{


	styleFunction(feature, resolution, selected=false, hovered=false){
		var valid = feature.get('valid');

		var color;
		if (valid){
			var zone = feature.get('zone');
			switch (zone){
				case "urban":
				palette.paletteUrban;
				break;
				case "rural":
				palette.paletteRural;
				break;
				default:
				palette = this.paletteUrban;
			}

			var d = feature.get('distance_overtaker_mean');
			color = palette.rgba_css(d)	
		} else {
			color = this.colorInvalid;
		}

		console.log("resolution: " + resolution);

	// var width = 2 + 1*Math.log10(n);
	var width = active?6:2;
	// width =Math.max(2.0, width*1/resolution);

	var style = new ol.style.Style({
		stroke: new ol.style.Stroke({
			color: color,
			width: width,
		})
	});
	return style;
	}

}


