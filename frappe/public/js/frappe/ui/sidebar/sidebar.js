import "./sidebar_item";
import { SidebarEditor } from "./sidebar_editor";
nts.ui.Sidebar = class Sidebar {
	constructor() {
		if (!nts.boot.setup_complete) {
			// no sidebar if setup is not complete
			return;
		}
		this.make_dom();
		// states
		this.editor = new SidebarEditor(this);
		this.edit_mode = this.editor.edit_mode;
		this.sidebar_expanded = false;
		this.all_sidebar_items = nts.boot.workspace_sidebar_item;
		this.$items = [];
		this.fields_for_dialog = [];
		this.workspace_sidebar_items = [];
		this.$items_container = this.wrapper.find(".sidebar-items");
		this.$standard_items_sections = this.wrapper.find(".standard-items-sections");
		this.$sidebar = this.wrapper.find(".body-sidebar");
		this.items = [];
		this.setup_events();
		this.sidebar_module_map = {};
		this.build_sidebar_module_map();
		this.standard_items_setup = false;
	}

	prepare() {
		try {
			this.add_standard_items();
			this.sidebar_data = nts.boot.workspace_sidebar_item[this.workspace_title];
			this.workspace_sidebar_items = this.sidebar_data.items;
			if (this.edit_mode) {
				this.workspace_sidebar_items = this.editor.new_sidebar_items;
			}
			this.choose_app_name();
			this.find_nested_items();
		} catch (e) {
			console.log(e);
		}
	}
	build_sidebar_module_map() {
		for (const [key, value] of Object.entries(nts.boot.workspace_sidebar_item)) {
			if (value.module && !value.label.includes("My Workspaces")) {
				if (!this.sidebar_module_map[value.module]) {
					this.sidebar_module_map[value.module] = [];
				}
				this.sidebar_module_map[value.module].push(value.label);
			}
		}
	}
	choose_app_name() {
		if (nts.boot.app_name_style === "Default") return;

		for (const app of nts.boot.app_data) {
			if (
				app.workspaces.includes(this.sidebar_title) ||
				(nts.boot.workspace_sidebar_item[this.workspace_title] &&
					app.app_name == nts.boot.workspace_sidebar_item[this.workspace_title].app)
			) {
				this.header_subtitle = app.app_title;
				nts.current_app = app;
				this.app_logo_url = app.app_logo_url;
				return;
			}
		}

		const icon = nts.boot.desktop_icons.find((i) => i.label === this.sidebar_title);
		if (icon) {
			this.header_subtitle = icon.parent_icon;
		}

		if (this.sidebar_title == "My Workspaces") {
			this.header_subtitle = nts.session.user;
		}
	}

	find_nested_items() {
		const me = this;
		let currentSection = null;
		const updated_items = [];

		this.workspace_sidebar_items.forEach((item) => {
			item.nested_items = [];

			if (item.type === "Section Break") {
				currentSection = item;
				updated_items.push(item);
			} else if (currentSection && item.child) {
				item.parent = currentSection;
				currentSection.nested_items.push(item);
			} else {
				updated_items.push(item);
			}
		});
		this.workspace_sidebar_items = updated_items;
	}
	setup(workspace_title) {
		this.sidebar_title = workspace_title;
		this.check_for_private_workspace(workspace_title);
		this.workspace_title = this.sidebar_title.toLowerCase();

		this.prepare();
		this.$sidebar.attr("data-title", this.sidebar_title);
		this.sidebar_header = new nts.ui.SidebarHeader(this);
		this.make_sidebar();
	}
	check_for_private_workspace(workspace_title) {
		if (workspace_title == "private" || workspace_title == "Personal") {
			this.sidebar_title = "My Workspaces";
		}
	}
	setup_events() {
		const me = this;
		nts.router.on("change", function (router) {
			if (nts.route_options.sidebar) {
				nts.app.sidebar.setup(nts.route_options.sidebar);
			} else {
				nts.app.sidebar.set_workspace_sidebar(router);
			}
		});
		$(document).on("page-change", function () {
			nts.app.sidebar.toggle();
		});
		$(document).on("form-refresh", function () {
			nts.app.sidebar.toggle();
		});
	}

	toggle() {
		if (!nts.container.page.page) return;
		if (nts.container.page.page.hide_sidebar) {
			this.wrapper.hide();
		} else {
			this.wrapper.show();
			this.set_sidebar_for_page();
		}
	}
	make_dom() {
		this.load_sidebar_state();
		this.wrapper = $(
			nts.render_template("sidebar", {
				expanded: this.sidebar_expanded,
				avatar: nts.avatar(nts.session.user, "avatar-medium"),
				navbar_settings: nts.boot.navbar_settings,
			})
		).prependTo("body");
		this.$sidebar = this.wrapper.find(".sidebar-items");

		this.wrapper.find(".body-sidebar .collapse-sidebar-link").on("click", () => {
			this.toggle_width();
		});

		this.wrapper.find(".overlay").on("click", () => {
			this.close();
		});
	}

	set_active_workspace_item() {
		if (this.is_route_in_sidebar()) {
			this.active_item.addClass("active-sidebar");
			this.expand_parent_section();
		}
	}

	expand_parent_section() {
		if (!this.active_item) return;
		let active_section;
		$(".section-item").each((index, element) => {
			if (element.contains(this.active_item.get(0))) {
				active_section = element.dataset.id;
			}
		});

		if (active_section) {
			let section = this.get_item(active_section);
			if (section) {
				if (this.sidebar_expanded && section.collapsed) {
					section.open();
				}
			}
		}
	}

	get_item(name) {
		for (let item of this.items) {
			if (item.item.label === name) {
				return item;
			}
		}
	}

	is_route_in_sidebar() {
		let match = false;
		const that = this;
		$(".item-anchor").each(function () {
			let href = decodeURIComponent($(this).attr("href")?.split("?")[0].split("#")[0]);

			const path = decodeURIComponent(window.location.pathname);

			// ensure no trailing slash mismatch
			const clean_href = href.replace(/\/$/, "");
			const clean_path = path.replace(/\/$/, "");

			const isActive = clean_path === clean_href || clean_path.startsWith(clean_href + "/");

			if (href && isActive) {
				match = true;
				if (that.active_item) that.active_item.removeClass("active-sidebar");
				that.active_item = $(this).parent();
			}
		});
		return match;
	}

	set_sidebar_state() {
		this.load_sidebar_state();
		if (this.workspace_sidebar_items.length === 0) {
			this.sidebar_expanded = true;
		}

		this.expand_sidebar();
	}

	load_sidebar_state() {
		this.sidebar_expanded = true;
		if (localStorage.getItem("sidebar-expanded") !== null) {
			this.sidebar_expanded = JSON.parse(localStorage.getItem("sidebar-expanded"));
		}

		if (nts.is_mobile()) {
			this.sidebar_expanded = false;
		}
	}
	empty() {
		if (this.wrapper.find(".sidebar-items")[0]) {
			this.wrapper.find(".sidebar-items").html("");
		}
	}
	make_sidebar() {
		this.empty();
		this.wrapper.find(".collapse-sidebar-link").removeClass("hidden");
		if (this.editor.edit_mode) {
			this.create_sidebar(this.editor.new_sidebar_items);
		} else {
			this.create_sidebar(this.workspace_sidebar_items);
		}

		// Scroll sidebar to selected page if it is not in viewport.
		this.wrapper.find(".selected").length &&
			!nts.dom.is_element_in_viewport(this.wrapper.find(".selected")) &&
			this.wrapper.find(".selected")[0].scrollIntoView();

		this.set_active_workspace_item();
		this.set_sidebar_state();
	}
	create_sidebar(items) {
		this.empty();
		if (items && items.length > 0) {
			items.forEach((w) => {
				if (!w.display_depends_on || nts.utils.eval(w.display_depends_on)) {
					this.add_item(this.$items_container, w);
				}
			});
		} else {
			let no_items_message = $(
				"<div class='flex' style='padding: 30px'> No Sidebar Items </div>"
			);
			this.wrapper.find(".sidebar-items").append(no_items_message);
			this.wrapper.find(".collapse-sidebar-link").addClass("hidden");
		}
		if (this.edit_mode) {
			$(".edit-menu").removeClass("hidden");
		}
		this.handle_outside_click();
	}
	add_standard_items(items) {
		if (this.standard_items_setup) return;
		this.standard_items = [];
		if (!nts.is_mobile()) {
			this.standard_items.push({
				label: __("Search"),
				icon: "search",
				standard: true,
				type: "Button",
				id: "navbar-modal-search",
				suffix: {
					keyboard_shortcut: "Ctrl+K",
				},
				class: "navbar-search-bar hidden",
			});
		}
		this.standard_items.push({
			label: __("Notification"),
			icon: "bell",
			standard: true,
			type: "Button",
			class: "sidebar-notification hidden",
			onClick: () => {
				this.wrapper.find(".dropdown-notifications").toggleClass("hidden");
				if (nts.is_mobile()) {
					this.wrapper.removeClass("expanded");
				}
			},
		});
		this.standard_items.forEach((w) => {
			this.add_item(this.$standard_items_sections, w);
		});
		this.setup_awesomebar();
		this.setup_notifications();
		this.standard_items_setup = true;
	}
	get_workspace_for_module(module) {
		for (let i = 0; i < nts.boot.workspaces.pages.length; i++) {
			const workspace = nts.boot.workspaces.pages[i];
			if (workspace.module == module && !workspace.parent_page) {
				return workspace.name;
			}
		}
	}
	setup_awesomebar() {
		if (nts.boot.desk_settings.search_bar) {
			let awesome_bar = new nts.search.AwesomeBar();
			awesome_bar.setup("#navbar-modal-search");

			nts.search.utils.make_function_searchable(
				nts.utils.generate_tracking_url,
				__("Generate Tracking URL")
			);
			if (nts.model.can_read("RQ Job")) {
				nts.search.utils.make_function_searchable(function () {
					nts.set_route("List", "RQ Job");
				}, __("Background Jobs"));
			}
		}
	}
	setup_notifications() {
		if (nts.boot.desk_settings.notifications && nts.session.user !== "Guest") {
			this.notifications = new nts.ui.Notifications({ full_height: true });
		}
	}
	add_item(container, item) {
		this.items.push(
			this.make_sidebar_item({
				container: container,
				item: item,
			})
		);
	}
	make_sidebar_item(opts) {
		let class_name = `Type${nts.utils.to_title_case(opts.item.type).replace(/ /g, "")}`;

		return new nts.ui.sidebar_item[class_name](opts);
	}
	update_item(item, index) {}

	remove_item(item, index) {}

	toggle_width() {
		if (!this.sidebar_expanded) {
			this.open();
		} else {
			this.close();
		}
	}

	expand_sidebar() {
		let direction;
		if (this.sidebar_expanded) {
			this.wrapper.addClass("expanded");
			// this.sidebar_expanded = false
			direction = "right";
			$('[data-toggle="tooltip"]').tooltip("dispose");
			this.wrapper.find(".avatar-name-email").show();
		} else {
			this.wrapper.removeClass("expanded");
			// this.sidebar_expanded = true
			direction = "left";
			$('[data-toggle="tooltip"]').tooltip({
				boundary: "window",
				container: "body",
				trigger: "hover",
			});
			this.wrapper.find(".avatar-name-email").hide();
		}

		localStorage.setItem("sidebar-expanded", this.sidebar_expanded);
		this.wrapper
			.find(".body-sidebar .collapse-sidebar-link")
			.find("use")
			.attr("href", `#icon-panel-${direction}-open`);
		this.sidebar_header.toggle_width(this.sidebar_expanded);
		$(document).trigger("sidebar-expand", {
			sidebar_expand: this.sidebar_expanded,
		});
	}

	close() {
		this.sidebar_expanded = false;

		this.expand_sidebar();
		if (nts.is_mobile()) nts.app.sidebar.prevent_scroll();
	}
	open() {
		this.sidebar_expanded = true;
		this.expand_sidebar();
		this.set_active_workspace_item();
	}

	set_height() {
		$(".body-sidebar").css("height", window.innerHeight + "px");
		$(".overlay").css("height", window.innerHeight + "px");
		document.body.style.overflow = "hidden";
	}

	handle_outside_click() {
		document.addEventListener("click", (e) => {
			if (this.sidebar_header.drop_down_expanded) {
				if (!e.composedPath().includes(this.sidebar_header.app_switcher_dropdown)) {
					this.sidebar_header.toggle_dropdown_menu();
				}
			}
		});
	}

	prevent_scroll() {
		let main_section = $(".main-section");
		if (this.sidebar_expanded) {
			main_section.css("overflow", "hidden");
		} else {
			main_section.css("overflow", "");
		}
	}

	set_workspace_sidebar(router) {
		try {
			let route = nts.get_route();
			let view, entity_name;
			switch (route.length) {
				case 1:
					view = "Page";
					entity_name = route[1];
					break;
				case 2:
					view = route[0];
					entity_name = route[1];

					if (nts.boot.workspace_sidebar_item[entity_name.toLowerCase()]) {
						nts.app.sidebar.setup(entity_name);
						return;
					}
					break;
				case 3:
					view = route[0];
					entity_name = route[1];
					if (route[0] == "Workspaces" && route[1] == "private") {
						entity_name = route[2];
					}
					break;
				default:
					entity_name = route[1];
			}
			let sidebars = this.get_workspace_sidebars(entity_name);
			this.preffered_sidebars = sidebars;
			let module = router?.meta?.module;
			if (this.sidebar_title && sidebars.includes(this.sidebar_title)) {
				this.set_active_workspace_item();
				return;
			}
			if (module) {
				sidebars = this.filter_sidebars_from_app(
					sidebars,
					nts.boot.module_app[module.toLowerCase()]
				);
			}
			if (sidebars.length == 1) {
				nts.app.sidebar.setup(sidebars[0]);
			} else if (sidebars.length > 1) {
				let sidebar = this.get_workspace_for_module(module);
				if (sidebars.includes(this.get_workspace_for_module(module))) {
					nts.app.sidebar.setup(sidebar);
				}
			} else if (module) {
				this.show_sidebar_for_module(module);
			}
		} catch (e) {
			console.log(e);
		}

		this.set_active_workspace_item();
	}
	filter_sidebars_from_app(sidebars, app) {
		let filter_sidebars = [];
		sidebars.forEach((sidebar) => {
			if (
				!filter_sidebars.includes(sidebar) &&
				nts.boot.workspace_sidebar_item[sidebar.toLowerCase()].app === app
			) {
				filter_sidebars.push(sidebar);
			}
		});
		return filter_sidebars;
	}
	show_sidebar_for_module(module) {
		if (this.sidebar_title && this.preffered_sidebars.includes(this.sidebar_title)) {
			this.set_active_workspace_item();
			return;
		}
		if (this.sidebar_fixes && this.sidebar_title != module) return;
		let workspace_name = this.get_workspace_for_module(module);
		if (nts.boot.workspace_sidebar_item[module.toLowerCase()]) {
			nts.app.sidebar.setup(module);
		} else if (
			workspace_name &&
			nts.boot.workspace_sidebar_item[workspace_name.toLowerCase()]
		) {
			nts.app.sidebar.setup(workspace_name);
		} else {
			let sidebars =
				this.sidebar_module_map[module] &&
				this.sidebar_module_map[module].sort((a, b) => {
					return a.localeCompare(b);
				});
			if (nts.get_route())
				if (sidebars && sidebars.length) {
					nts.app.sidebar.setup(sidebars[0]);
				}
		}
	}
	set_sidebar_for_page() {
		let route = nts.get_route();
		let views = ["List", "Form", "Workspaces", "query-report"];
		let matches = views.some((view) => route.includes(view));
		if (matches) return;
		let workspace_title;
		if (route.length == 2) {
			workspace_title = this.get_workspace_sidebars(route[1]);
		} else {
			workspace_title = this.get_workspace_sidebars(route[0]);
		}
		let module_name = workspace_title[0];
		if (module_name) {
			nts.app.sidebar.setup(module_name || this.sidebar_title);
		}
	}

	get_workspace_sidebars(link_to) {
		let sidebars = [];
		Object.entries(this.all_sidebar_items).forEach(([name, sidebar]) => {
			const { items, label } = sidebar;
			if (label.includes("My Workspaces")) return;
			items.forEach((item) => {
				if (item.link_to === link_to) {
					sidebars.push(label || name);
				}
			});
		});
		return sidebars;
	}
};
