class InteractiveVisualization {
    constructor(map, dataSource) {
        this.featureFormatter = new FeatureStyle();

        this.activeFeature = undefined;
        this.hoveredFeature = undefined;

        this.map = map;
        this.dataSource = dataSource;

        this.menu = new Menu("vis-menu");

        this.representations = [];

		// map.on('singleclick', function (event){this.onSingleClick(event)});
		// map.on('pointermove', function (event){this.onPointerMove(event)});

		map.on('singleclick', event => this.onSingleClick(event));
		map.on('pointermove', event => this.onPointerMove(event));
    }

    addRepresentation(path, representation){
        this.representations.push(representation);
        const i = this.representations.length - 1;
        this.menu.addMenu(path, "visualization.selectRepresentation(" + i + ")");
    }

    selectRepresentation(ix){
        console.log("selected representation " + ix);
        this.setFeatureFormatter(this.representations[ix]);
    }

    setFeatureFormatter(featureFormatter) {
        if (this.featureFormatter) {
            this.featureFormatter.deselect();
        }
        this.featureFormatter = featureFormatter;
        featureFormatter.select();
    }

    styleFunction(feature, resolution, selected=false, hovered=false){
        if (this.featureFormatter){
            return this.featureFormatter.styleFunction(feature, resolution, selected, hovered);
        }
    }

    onPointerMove(event) {
        if (event.dragging) {
            return;
        }

        const feature = map.forEachFeatureAtPixel(this.map.getEventPixel(event.originalEvent),
            function (feature, layer) {
                return feature;
            });

        const resolution = map.getView().getResolution();

        if (this.hoveredFeature) {
            this.hoveredFeature.setStyle(this.featureFormatter.styleFunction(this.hoveredFeature, resolution, this.hoveredFeature == this.activeFeature, false));
            this.hoveredFeature = undefined;
        }

        if (feature && dataSource.hasFeature(feature)) {
            feature.setStyle(this.featureFormatter.styleFunction(feature, resolution, feature == this.activeFeature, true));
            this.hoveredFeature = feature;
        }
    }

    onSingleClick(event) {
        const feature = this.map.forEachFeatureAtPixel(event.pixel,
            function (feature, layer) {
                return feature;
            });

        const resolution = map.getView().getResolution();

        if (this.activeFeature) {
            this.activeFeature.setStyle(this.featureFormatter.styleFunction(activeFeature, resolution, false, this.activeFeature == this.hoveredFeature));
            this.activeFeature = undefined;
        }

        if (feature && this.dataSource.hasFeature(feature)) {
            feature.setStyle(this.featureFormatter.styleFunction(feature, resolution, true, feature == this.hoveredFeature));
            this.activeFeature = feature;
        }
    }

}