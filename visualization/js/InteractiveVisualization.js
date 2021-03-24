class InteractiveVisualization {
    constructor(map, dataSource) {
        this.featureFormatter = new FeatureStyle();

        this.activeFeature = undefined;
        this.hoveredFeature = undefined;

        this.map = map;
        this.dataSource = dataSource;
    }


    setFeatureFormatter(featureFormatter) {
        if (this.featureFormatter) {
            this.featureFormatter.deselect();
        }
        this.featureFormatter = featureFormatter;
        featureFormatter.select();
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
            this.hoveredFeature.setStyle(this.featureFormatter.styleFunction(hoveredFeature, resolution, this.hoveredFeature == this.activeFeature, false));
            this.hoveredFeature = undefined;
        }

        if (feature && dataSource.hasFeature(feature)) {
            feature.setStyle(this.featureFormatter.styleFunction(feature, resolution, feature == activeFeature, true));
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


