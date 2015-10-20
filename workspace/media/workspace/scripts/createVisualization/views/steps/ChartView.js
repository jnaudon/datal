var ChartView = StepViewSPA.extend({

	bindings: {
	    "p.message": "text:message"
	},

	initialize: function(options){

		this.stateModel = options.stateModel;

		// Right way to extend events without overriding the parent ones
		this.addEvents({
	
			'click .step-1-view a.backButton': 			'onPreviousButtonClicked',
			'click .step-1-view a.nextButton': 			'onNextButtonClicked',
			'click button.selectData': 		'onSelectDataClicked',
			'click button.chartType': 		'onChartTypeClicked',
			'change select#chartLibrary': 	'onChartLibraryChanged',
			
			'keyup input#nullValuePreset': 	'onInputChanged',
			
			'change input[type=radio]': 	'onRadioChanged',
			'change input[type=checkbox]': 	'onCheckboxChanged',
			'click div.chartContent': 		'onChartContentClicked'

		});

		this.chartsFactory = new charts.ChartsFactory(); // create ChartsFactory

        this.modalView = new ChartSelectDataModalView({
          el: '#ChartSelectDataModal',
          model: this.model,
          dataStreamModel: options.dataStreamModel
        });
        this.modalView.on('open', function () {
        	this.model.set('select_data',true);
        	if(this.dataTableView){
        		this.dataTableView.render();
        	}
        });

		this.vizContent = this.$el.find('.visualizationContainer');
		this.chartContent = this.$el.find('.chartContent');
		this.selectDataBtn = this.$el.find('.visualizationContainer button.selectData');
		this.nextBtn = this.$el.find('a.nextButton');
		this.message = this.$el.find('p.message');
		this.optionsItemConfig = this.$el.find('div.optionsItemConfig');

		//edit
		if(this.stateModel.get('isEdit') && !this.stateModel.get('isMap')){
			var that = this;
			
			//library
			this.$el.find('select#chartLibrary').val(this.model.get('lib'));
			
			//checkbox
			this.$el.find('input[type=checkbox]').each(function(){
				var obj = $(this);
				var name = obj.attr('name');
				if(that.model.get(name)){
					obj.prop("checked","checked")
				}
			});

			//radio
			var that = this;
			this.$el.find('input[type=radio]').each(function(){
				var obj = $(this);
				var name = obj.attr('name');
				if(that.model.get(name)==obj.val()){
					obj.prop("checked","checked")
				}
			});

			//nullValue
			this.$el.find('input#nullValuePreset').val(this.model.get('nullValuePreset'));

			$("#ajax_loading_overlay").show();

			//this.renderChart();
		} else {
			this.optionsItemConfig.hide();
		}

		this.nextBtn.addClass('disabled');

		this.setupChart();

	},

	bgClasses: {
			'barchart': 'previewBar',
			'columnchart': 'previewColumn',
			'areachart': 'previewArea',
			'linechart': 'previewLine',
			'piechart': 'previewPie'
	},	

	onCloseModal: function () {
		this.fetchPreviewData();
	},

	fetchPreviewData: function(){
		$("#ajax_loading_overlay").show();
		this.model.fetchData()
		.then(function () {
			$("#ajax_loading_overlay").hide();
		})
		.error(function(response){
			$("#ajax_loading_overlay").hide();
        });;
	},

	onCheckboxChanged: function(e){
		var input = $(e.target);
		this.model.set(input.attr('name'), input.prop('checked') );
		this.fetchPreviewData();
	},

	onChangeData: function () {
		if(this.selectDataBtn.hasClass('icon-add')){
			this.selectDataBtn.removeClass('icon-add').addClass('icon-edit');		
			this.vizContent.addClass('dataSelected');
		}
		$("#ajax_loading_overlay").hide();
		console.log('the data for your chart has changed', this.model.data.toJSON());
		//this.optionsItemConfig.show();
		// TODO: should call this.chartView.render();
		this.renderChart();
	},

	onChartContentClicked: function(){
		if(!this.chartInstance || !this.chartInstance.chart){
			this.modalView.open();
		}
	},

	onSelectDataClicked: function(){
		this.modalView.open();
	},

	onChartTypeClicked: function(e){
		e.preventDefault();
		var type = $(e.currentTarget).data('type');
		this.selectGraphType(type);
	},

	onChartLibraryChanged: function(e){
		var lib = $(e.currentTarget).val();
		$('.chartType').hide();
		$('.chartType.'+lib+'Chart').show();
		this.model.set('lib',lib);
	},

	onInputChanged: function(e){
		var input = $(e.currentTarget);
			value = input.val();

		var valid = this.model.set(input.data('ref'), input.val(), {validate: true});

		if (valid) {
			this.fetchPreviewData();
			input.removeClass('has-error');
			this.nextBtn.removeClass('enabled');
		} else {
			console.error(this.model.validationError);
			input.addClass('has-error');
			this.nextBtn.addClass('disabled');
		}
	},

	onRadioChanged: function(e){
		var input = $(e.currentTarget);
		this.model.set(input.attr('name'), input.val());

		if(input.val()=='given'){
			$('#nullValuePreset').show();
		}else{
			this.fetchPreviewData();
			this.model.unset('nullValuePreset');
			$('#nullValuePreset').hide().val('');
		}
	},

	selectGraphType: function(type){
		$('.chartType').removeClass('active');
		$('.chartType.'+type).addClass('active');
		this.updatePreviewClass(type);
		this.model.set('type',type);
	},

	updatePreviewClass: function(type){
		this.clearClassesChartBg();
		if(!this.ChartViewClass){
			this.chartContent.addClass(this.bgClasses[type]);
		}
	},

	clearClassesChartBg: function(){
		var that = this;
		_.each(this.bgClasses, function(clase){
			that.chartContent.removeClass(clase);			
		});
	},

	onChartChanged: function(){
		if(!this.stateModel.get('isMap')){
			console.log('you selected type: ', this.model.get('type') + ' - '+ this.model.get('lib') );
			this.setupChart();
			this.renderChart();
		}
	},

	setupChart: function(){

		var chartSettings = this.chartsFactory.create(this.model.get('type'),this.model.get('lib'));

		if(chartSettings){

			//change visibility of controls
			$('.attributeControl').hide();
			_.each(chartSettings.attributes,function(e){
				$('.attributeControl.'+e+'AttributeControl').show();
			});

			//Set list of custom attributes for my model
			this.model.set('attributes',chartSettings.attributes);

			this.ChartViewClass = chartSettings.Class;

		} else {
			delete this.ChartViewClass;
			console.log('There are not class for this');
		}

	},

	renderChart: function () {
	
		if (this.ChartViewClass) {

			this.destroyChartInstance();

			this.chartInstance = new this.ChartViewClass({
				el: this.chartContent,
				model: this.model,
			});
			
			//Validate data
			var validation = this.model.valid(); //valida datos por tipo de gráfico

			if(validation===true){
				if(this.model.get('select_data')){ //si alguna vez abrió el modal de datos
					this.clearClassesChartBg();
					this.nextBtn.removeClass('disabled');
					this.message.hide();
					this.chartInstance.render();
					this.optionsItemConfig.show();
				} else {
					this.nextBtn.addClass('disabled');
					this.chartContent.addClass(this.bgClasses[this.model.get('type')]);
					this.vizContent.removeClass('dataSelected');
					this.optionsItemConfig.hide();
				}
			}	else {
				this.message.show();
				this.destroyChartInstance();
				this.nextBtn.addClass('disabled');
				this.vizContent.removeClass('dataSelected');
				this.chartContent.addClass(this.bgClasses[this.model.get('type')]);
				this.optionsItemConfig.hide();
			}
		}
	},

	destroyChartInstance: function(){
		if(this.chartInstance){
			this.chartInstance = this.chartInstance.destroy();
		}
	},

	onPreviousButtonClicked: function(){
		this.previous();
	},

	onNextButtonClicked: function(){		
		this.next();
	},

	start: function(){
		this.constructor.__super__.start.apply(this);

		//this.listenTo(this.model.data, 'change:rows', this.onChangeData, this);
		this.listenTo(this.model, 'data_updated',this.onChangeData,this);
		this.listenTo(this.model, 'change:lib', this.onChartChanged, this);
		this.listenTo(this.model, 'change:type', this.onChartChanged, this);
		this.listenTo(this.modalView, 'close', this.onCloseModal, this);

		// chart type from first step
		var initial = this.model.get('type');
		this.selectGraphType(initial);

		if(this.model.data.get('rows').length){
			this.onChartChanged();
		}

	},

	finish: function(){
		this.constructor.__super__.finish.apply(this);
		this.stopListening();

		if(this.chartInstance){
			this.chartInstance.destroy();
		}
	},



});