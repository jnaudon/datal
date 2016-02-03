var ModalView = Backbone.View.extend({
	events: {
        'click button.btn-done':'onClickDone',
		'click button.btn-cancel':'onClickCancel'
	},

	initialize: function(options){
        // models
        this.collection = new DataTableSelectedCollection();
        this.dataStreamModel = options.dataStreamModel;

        this.rangeLatModel = new DataTableSelectionModel({classname: 1, mode: 'lat', name: 'latitudSelection', notEmpty: true});
        this.rangeLonModel = new DataTableSelectionModel({classname: 2, mode: 'lon', name: 'longitudSelection', notEmpty: true});
        this.rangeInfoModel = new DataTableSelectionModel({classname: 3, mode: 'data', name: 'data', notEmpty: true});
        this.rangeTraceModel = new DataTableSelectionModel({classname: 4, mode: 'trace', name: 'traceSelection', notEmpty: true});

        this.rangeDataModel = new DataTableSelectionModel({classname: 1, mode: 'data', name: 'data', notEmpty: true});
        this.rangeLabelsModel = new DataTableSelectionModel({classname: 2, mode: 'labels', name: 'labelSelection', notEmpty: true});
        this.rangeHeadersModel = new DataTableSelectionModel({classname: 3, mode: 'headers', name: 'headerSelection', notEmpty: true});

        // subviews
        this.selectedCellRangeView = new SelectedCellRangeView({
            el: this.$('.selected-ranges-view'),
            model: this.model,
            collection: this.collection
        });

        // events
        this.on('open', this.onOpen, this);
        this.listenTo(this.dataStreamModel.data, 'change:rows', this.onLoadDataStream, this);
        this.listenTo(this.model, 'change:type', this.onChangeType, this);
        this.listenTo(this.model, 'change:geoType', this.onChangeType, this);
        this.listenTo(this.collection, 'change remove reset', this.validate, this);
        this.listenTo(this.selectedCellRangeView, 'focus-input', function (name) {
            this._cacheFocusedInput = name;
        });

        // initialization
        this.onChangeType();
        return this;
    },

    onOpen: function () {
        this.selectedCellRangeView.render();

        this.rangeLatModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('latitudSelection')));
        this.rangeLonModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('longitudSelection')));
        this.rangeInfoModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('data')));
        this.rangeTraceModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('traceSelection')));
        this.rangeDataModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('data')));
        this.rangeLabelsModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('labelSelection')));
        this.rangeHeadersModel.set('excelRange', DataTableUtils.parseEngineExcelRange(this.model.get('headerSelection')));

        this.collection.setCache();
        this.setHeights();
        this.setAxisTitles();
    },

    onChangeType: function () {
        var type = this.model.get('type'),
            geoType = this.model.get('geoType');

        if (type === 'mapchart') {
            if (geoType === 'points') {
                this.collection.reset([this.rangeLatModel, this.rangeLonModel, this.rangeInfoModel]);
            } else if (geoType === 'traces') {
                this.collection.reset([this.rangeTraceModel, this.rangeInfoModel]);
            }
        } else {
            this.collection.reset([this.rangeDataModel, this.rangeLabelsModel, this.rangeHeadersModel]);
        }
    },

    onClickDone: function (e) {
        var result = this.collection.reduce(function (memo, m) {
            memo[m.get('name')] = DataTableUtils.toServerExcelRange(m.get('excelRange'));
            return memo;
        }, {});
        // Revisar los filtros para pedir el mejor mapa posible
        result = this.fixMapInitialData(result);
        this.model.set(result);
        this.close();
    },

    // al aplicar estos resultados se llamará al motor para traer los datos.
    // si es un mapa, tomar los datos (el primer punto), definirlo como centro 
    // y definir un zoom menor    
    fixMapInitialData: function(result) {
        var type = this.model.get('type'), geoType = this.model.get('geoType');

        if (type === 'mapchart') {
            data = this.dataStreamModel.data;
            // defs
            row = data.attributes.rows[1]; //tomo la primera fila
            center = {lat: 0, long: 0};
            bounds = [85,180,-85,-180];
            if (geoType === 'points') {
                latRange = result.latitudSelection;
                lonRange = result.longitudSelection;
                lars = latRange.split(':');
                lors = lonRange.split(':');
                if (lars[0] == 'Column') { // Column:F por ejemplo
                    center.lat = parseFloat(row[lars[1].charCodeAt(0) - 65]); // A = 0, B = 1, etc
                    center.long = parseFloat(row[lors[1].charCodeAt(0) - 65]); // A = 0, B = 1, etc
                    bounds = [center.lat + 5, center.long + 5, center.lat - 5, center.long - 5];
                }
                else { // F3:F28 por ejemplo
                    // separar numeros de letras
                    letter1 = lars[0].split('')[0];
                    letter2 = lors[0].split('')[0];
                    rown = parseInt(lars[0].split('').slice(1).join('')) + 1; // evitar posible header
                    row = data.attributes.rows[rown]; 
                    center.lat = parseFloat(row[letter1.charCodeAt(0) - 65]); // A = 0, B = 1, etc
                    center.long = parseFloat(row[letter2.charCodeAt(0) - 65]); // A = 0, B = 1, etc
                    bounds = [center.lat + 5, center.long + 5, center.lat - 5, center.long - 5];
                }
                        
            } else if (geoType === 'traces') {
                traceRange = result.traceSelection
                tars = traceRange.split(':');
                if (tars[0] == 'Column') { // Column:F por ejemplo
                    trace = row[tars[1].charCodeAt(0) - 65]; // A = 0, B = 1, etc
                    // al parecer son una serie de puntos LONG, LAT, ...
                    center.lat = parseFloat(trace.split(',')[1]); 
                    center.long = parseFloat(trace.split(',')[0]); 
                    bounds = [center.lat + 5, center.long + 5, center.lat - 5, center.long - 5];
                }
                else { // F3:F28 por ejemplo
                    // separar numeros de letras
                    letter = tars[0].split('')[0];
                    rown = parseInt(tars[0].split('').slice(1).join('')) + 1; // evitar posible header
                    row = data.attributes.rows[rown]; 
                    trace = row[letter.charCodeAt(0) - 65]; // A = 0, B = 1, etc
                    center.lat = parseFloat(trace.split(',')[1]); 
                    center.long = parseFloat(trace.split(',')[0]);
                    bounds = [center.lat + 5, center.long + 5, center.lat - 5, center.long - 5];
                }
            }
            result.options = {zoom: 13, center: center, bounds: bounds};
        }
    return result;
    },

    onClickCancel: function (e) {
        this.collection.revert();
        this.onClickDone();
        this.close();
    },

    /* se cargaron los datos del datastream, estan en dataviewModel.toJSON() */
    onLoadDataStream: function (dataviewModel) {
        this.dataTableView = new DataTableView({
            el: this.$('.data-table-view'),
            collection: this.collection,
            dataview: dataviewModel.toJSON()
        });
        this.dataTableView.render();
        this.collection.setMaxCols(this.dataTableView.table.countCols());
        this.collection.setMaxRows(this.dataTableView.table.countSourceRows());
        this.listenTo(this.dataTableView, 'afterSelection', function (range) {
            this.addSelection(this._cacheFocusedInput);
        }, this);
        this.listenTo(this.dataTableView, 'afterSelectionEnd', function () {
            this.addSelection(this._cacheFocusedInput);
        }, this);
    },

    addSelection: function (name) {
        var selection = this.dataTableView.getSelection(),
            model = this.collection.find(function (model) {
                return model.get('name') === name;
            });
        model.set(selection);
        var mode = [this._cacheFocusedInput, selection.mode].join('_');
        // console.log(selection, mode);

        this.validate();
    },

    validate: function () {
        var type = this.model.get('type'),
            geoType = this.model.get('geoType'),
            valid = false;

        if (type === 'mapchart') {
            if (geoType === 'points') {
                valid = this.validateLatLon();
            } else if (geoType === 'traces') {
                valid = this.validateTrace();
            }
        } else {
            valid = this.validateData();
        }

        if (valid) {
            this.enable();
        } else {
            this.disable();
        }
    },

    validateLatLon: function () {
        var hasLat = this.rangeLatModel.hasRange(),
            hasLon = this.rangeLonModel.hasRange(),
            hasInfo = this.rangeInfoModel.hasRange(),
            validLat = this.rangeLatModel.isValid(),
            validLon = this.rangeLonModel.isValid(),
            validInfo = this.rangeInfoModel.isValid();

        return hasLat && hasLon && hasInfo && validLat && validLon && validInfo;
    },

    validateTrace: function () {
        var hasTrace = this.rangeTraceModel.hasRange(),
            hasInfo = this.rangeInfoModel.hasRange(),
            validTrace = this.rangeTraceModel.isValid(),
            validInfo = this.rangeInfoModel.isValid();

        return hasTrace && hasInfo && validTrace && validInfo;
    },

    validateData: function () {
        var hasData = this.rangeDataModel.hasRange(),
            hasLabels = this.rangeLabelsModel.hasRange(),
            hasHeaders = this.rangeHeadersModel.hasRange(),
            validData = this.rangeDataModel.isValid(),
            validLabels = this.rangeLabelsModel.isValid(),
            validHeaders = this.rangeHeadersModel.isValid();

        return hasData && hasLabels && hasHeaders && validData && validLabels && validHeaders 
            && this.validateDataHeaders(this.rangeDataModel, this.rangeHeadersModel);
    },

    validateDataHeaders: function(validData, validHeaders) {
        if (validData && validHeaders) {
            var dataCols = validData.getRange().to.col - validData.getRange().from.col + 1;
            var headersRows = validHeaders.getRange().to.row - validHeaders.getRange().from.row + 1;
            if (validHeaders.getRange().to.row == -1 || validHeaders.getRange().from.row == -1) {
                headersRows = 0;
            }
            var headersCols = validHeaders.getRange().to.col - validHeaders.getRange().from.col + 1;
            return dataCols == headersCols * headersRows
        }
        return false
    },

    enable: function () {
        this.$('button.btn-done').removeAttr('disabled');
    },

    disable: function () {
        this.$('button.btn-done').attr('disabled', 'disabled');
    },

    setHeights: function(t){
        var self = this;

        var sidebar = this.$el.find('.sidebar'),
            table = this.$el.find('.table-view');

        $(window).resize(function(){

            windowHeight = $(window).height();

            var sidebarHeight =
              windowHeight
            - parseFloat( self.$el.find('.context-menu').height() )
            - parseFloat( sidebar.parent().css('padding-top').split('px')[0] )
            - 50 // As margin bottom
            ;

            sidebar.css('height', sidebarHeight+'px');
            table.css('height', sidebarHeight+'px');

        }).resize();
    },

    setAxisTitles: function(){
        var invertedAxis = (_.isUndefined(this.model.get('invertedAxis')))?'false':this.model.get('invertedAxis');
        var invertedAxisClass = 'invertedAxis-' + invertedAxis;
        this.$('.invertedAxisLabel').hide();
        this.$('.'+invertedAxisClass).show();
    },

    open: function(){
        $('body').css('overflow', 'hidden');
        $('.process-manager-modal').addClass('hidden');
        this.$el.removeClass('hidden');
        this.trigger('open');
    },

    close: function(){
        $('body').css('overflow', 'auto');
        this.$el.addClass('hidden');
        this.trigger('close');
    }

});
