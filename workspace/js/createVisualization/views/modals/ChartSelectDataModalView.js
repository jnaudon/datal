var ChartSelectDataModalView = ModalView.extend({
	events: {
        'click button.btn-done':'onClickDone',
		'click button.btn-cancel':'onClickCancel'
	},

	initialize: function(){
		var self = this;

		//init table
		this.collection = new DataTableSelectedCollection();

        this.rangeDataModel = new DataTableSelectionModel({id: 1});
        this.rangeLabelsModel = new DataTableSelectionModel({id: 2});
        this.rangeHeadersModel = new DataTableSelectionModel({id: 3});

        this.selectedCellRangeView = new SelectedCellRangeView({
            el: this.$('.selected-ranges-view'),
            collection: this.collection
        });

        this.listenTo(this.selectedCellRangeView, 'focus-input', function (name) {
            this._cacheFocusedInput = name;
        });

        this.listenTo(this.selectedCellRangeView, 'edit-input', function (name, val) {
            console.log('edit-input', name, val);
            // this.dataTableView.selectRange(val);
        });

        var dataUrl = ['/dataviews/invoke?datastream_revision_id=', 
            this.model.get('datastream_revision_id'),
            '&limit=50&page=0'].join('');

        // TODO: this is fetching data from the invoke endpoint which will be deprecated. Change the
        // request when it fails.
        $.getJSON(dataUrl).then(function (payload) {
            self.createDataTableView(payload);
        });

        this.on('open', function () {
            this.selectedCellRangeView.focus();
            this.setHeights();
        }, this);

        this.listenTo(this.collection, 'add change remove reset', this.validate, this);

        return this;
    },

    onClickDone: function (e) {
        this.model.set({
            range_data: this.rangeDataModel.getExcelRange(),
            range_headers: this.rangeHeadersModel.getExcelRange(),
            range_labels: this.rangeLabelsModel.getExcelRange()
        });
        this.close();
    },

    onClickCancel: function (e) {
        this.collection.reset();
        this.selectedCellRangeView.clear();
        this.close();
    },

    createDataTableView: function (payload) {
        this.dataTableView = new DataTableView({
            el: this.$('.data-table-view'),
            collection: this.collection,
            invoke: payload
        });
        this.dataTableView.render();
        this.listenTo(this.dataTableView, 'afterSelection', function (range) {
            this.selectedCellRangeView.select(range);
        }, this);
        this.listenTo(this.dataTableView, 'afterSelectionEnd', function () {
            this.addSelection(this._cacheFocusedInput);
            // this.selectedCellRangeView.focusNext();
        }, this);
        this.dataTableView.table.render();
    },

    addSelection: function (name) {
        var selection = this.dataTableView.getSelection(),
            model;

        if (name === 'range_data') {
            this.collection.remove(1);
            model = this.rangeDataModel;
        } else if (name === 'range_labels') {
            this.collection.remove(2);
            model = this.rangeLabelsModel;
        } else if (name === 'range_headers') {
            this.collection.remove(3);
            model = this.rangeHeadersModel;
        }
        model.set(selection);

        if (model.isValid()) {
            this.collection.add(model);
        } else {
            alert(model.validationError)
        }
    },

    validate: function () {
        if (this.collection.length < 3) {
            this.$('button.btn-done').attr('disabled', 'disabled');
        } else {
            this.$('button.btn-done').removeAttr('disabled');
        }
    },

    setHeights: function(t){
        var self = this;

        var sidebar = $('.modal').find('.sidebar'),
            table = $('.modal').find('.table-view');

        $(window).resize(function(){

            windowHeight = $(window).height();
            
            var sidebarHeight =
              windowHeight
            - parseFloat( $('.modal').find('.context-menu').height() )
            - parseFloat( sidebar.parent().css('padding-top').split('px')[0] )
            - 30 // As margin bottom
            ;

            sidebar.css('height', sidebarHeight+'px');
            table.css('height', sidebarHeight+'px');

        }).resize();
    }, 
});