nts.listview_settings["File"] = {
	formatters: {
		file_name: function (value) {
			return nts.utils.escape_html(value || "");
		},
	},
};
