nts.ui.form.on("User", {
	setup: function (frm) {
		frm.set_query("default_workspace", () => {
			return {
				filters: {
					for_user: ["in", [null, nts.session.user]],
					title: ["!=", "Welcome Workspace"],
				},
			};
		});
	},
	before_load: function (frm) {
		let update_tz_options = function () {
			frm.fields_dict.time_zone.set_data(nts.all_timezones);
		};

		if (!nts.all_timezones) {
			nts.call({
				method: "nts.core.doctype.user.user.get_timezones",
				callback: function (r) {
					nts.all_timezones = r.message.timezones;
					update_tz_options();
				},
			});
		} else {
			update_tz_options();
		}
	},

	time_zone: function (frm) {
		if (frm.doc.time_zone && frm.doc.time_zone.startsWith("Etc")) {
			frm.set_df_property(
				"time_zone",
				"description",
				__("Note: Etc timezones have their signs reversed.")
			);
		}
	},

	module_profile: function (frm) {
		if (frm.doc.module_profile) {
			nts.call({
				method: "nts.core.doctype.user.user.get_module_profile",
				args: {
					module_profile: frm.doc.module_profile,
				},
				callback: function (data) {
					frm.set_value("block_modules", []);
					$.each(data.message || [], function (i, v) {
						let d = frm.add_child("block_modules");
						d.module = v.module;
					});

					// if I am able to edit module profile,
					// module editor should always be available, but just in case
					if (frm.module_editor) {
						frm.module_editor.disable = 1;
						frm.module_editor.show();
					}
				},
			});
		}
	},

	onload: function (frm) {
		frm.can_edit_roles = has_access_to_edit_user();

		if (frm.is_new() && frm.roles_editor) {
			frm.roles_editor.reset();
		}

		if (
			frm.can_edit_roles &&
			!frm.is_new() &&
			["System User", "Website User"].includes(frm.doc.user_type)
		) {
			if (!frm.roles_editor) {
				const role_area = $('<div class="role-editor">').appendTo(
					frm.fields_dict.roles_html.wrapper
				);

				frm.roles_editor = new nts.RoleEditor(
					role_area,
					frm,
					frm.doc.role_profiles && frm.doc.role_profiles.length ? 1 : 0
				);

				if (frm.doc.user_type == "System User") {
					var module_area = $("<div>").appendTo(frm.fields_dict.modules_html.wrapper);
					frm.module_editor = new nts.ModuleEditor(
						frm,
						module_area,
						frm.doc.module_profile ? 1 : 0
					);
				}
			} else {
				frm.roles_editor.show();
			}
		}
	},
	refresh: function (frm) {
		let doc = frm.doc;

		nts.xcall("nts.apps.get_apps").then((r) => {
			let apps = r?.map((r) => r.name) || [];
			frm.set_df_property("default_app", "options", [" ", ...apps]);
		});

		if (frm.is_new()) {
			frm.set_value("time_zone", nts.sys_defaults.time_zone);
		}

		if (
			["System User", "Website User"].includes(frm.doc.user_type) &&
			!frm.is_new() &&
			!frm.roles_editor &&
			frm.can_edit_roles
		) {
			frm.reload_doc();
			return;
		}

		frm.toggle_display(["sb1", "sb3", "modules_access"], false);
		frm.trigger("setup_impersonation");

		if (!frm.is_new()) {
			if (has_access_to_edit_user()) {
				frm.add_custom_button(
					__("Set User Permissions"),
					function () {
						nts.route_options = {
							user: doc.name,
						};
						nts.set_route("List", "User Permission");
					},
					__("Permissions")
				);

				frm.add_custom_button(
					__("View Permitted Documents"),
					() =>
						nts.set_route("query-report", "Permitted Documents For User", {
							user: frm.doc.name,
						}),
					__("Permissions")
				);

				frm.add_custom_button(
					__("View Doctype Permissions"),
					() =>
						nts.set_route("query-report", "User Doctype Permissions", {
							user: frm.doc.name,
						}),
					__("Permissions")
				);

				frm.toggle_display(["sb1", "sb3", "modules_access"], true);
			}

			frm.add_custom_button(
				__("Reset Password"),
				function () {
					nts.call({
						method: "nts.core.doctype.user.user.reset_password",
						args: {
							user: frm.doc.name,
						},
					});
				},
				__("Password")
			);

			if (nts.user.has_role("System Manager")) {
				nts.db.get_single_value("LDAP Settings", "enabled").then((value) => {
					if (value === 1 && frm.doc.name != "Administrator") {
						frm.add_custom_button(
							__("Reset LDAP Password"),
							function () {
								const d = new nts.ui.Dialog({
									title: __("Reset LDAP Password"),
									fields: [
										{
											label: __("New Password"),
											fieldtype: "Password",
											fieldname: "new_password",
											reqd: 1,
										},
										{
											label: __("Confirm New Password"),
											fieldtype: "Password",
											fieldname: "confirm_password",
											reqd: 1,
										},
										{
											label: __("Logout All Sessions"),
											fieldtype: "Check",
											fieldname: "logout_sessions",
										},
									],
									primary_action: (values) => {
										d.hide();
										if (values.new_password !== values.confirm_password) {
											nts.throw(__("Passwords do not match!"));
										}
										nts.call(
											"nts.integrations.doctype.ldap_settings.ldap_settings.reset_password",
											{
												user: frm.doc.email,
												password: values.new_password,
												logout: values.logout_sessions,
											}
										);
									},
								});
								d.show();
							},
							__("Password")
						);
					}
				});
			}

			if (
				cint(nts.boot.sysdefaults.enable_two_factor_auth) &&
				(nts.session.user == doc.name || nts.user.has_role("System Manager"))
			) {
				frm.add_custom_button(
					__("Reset OTP Secret"),
					function () {
						nts.call({
							method: "nts.twofactor.reset_otp_secret",
							args: {
								user: frm.doc.name,
							},
						});
					},
					__("Password")
				);
			}

			frm.trigger("enabled");

			if (frm.roles_editor && frm.can_edit_roles) {
				frm.roles_editor.disable =
					frm.doc.role_profiles && frm.doc.role_profiles.length ? 1 : 0;
				frm.roles_editor.show();
			}

			if (frm.module_editor) {
				frm.module_editor.disable = frm.doc.module_profile ? 1 : 0;
				frm.module_editor.show();
			}

			if (nts.session.user == doc.name) {
				// update display settings
				if (doc.user_image) {
					nts.boot.user_info[nts.session.user].image = nts.utils.get_file_link(
						doc.user_image
					);
				}
			}
		}
		if (frm.doc.user_emails && nts.model.can_create("Email Account")) {
			var found = 0;
			for (var i = 0; i < frm.doc.user_emails.length; i++) {
				if (frm.doc.email == frm.doc.user_emails[i].email_id) {
					found = 1;
				}
			}
			if (!found) {
				frm.add_custom_button(__("Create User Email"), function () {
					if (!frm.doc.email) {
						nts.msgprint(__("Email is mandatory to create User Email"));
						return;
					}
					frm.events.create_user_email(frm);
				});
			}
		}

		if (nts.route_flags.unsaved === 1) {
			delete nts.route_flags.unsaved;
			for (let i = 0; i < frm.doc.user_emails.length; i++) {
				frm.doc.user_emails[i].idx = frm.doc.user_emails[i].idx + 1;
			}
			frm.dirty();
		}
		frm.trigger("time_zone");
	},
	validate: function (frm) {
		if (frm.roles_editor) {
			frm.roles_editor.set_roles_in_table();
		}
	},
	enabled: function (frm) {
		var doc = frm.doc;
		if (!frm.is_new() && has_access_to_edit_user()) {
			frm.toggle_display(["sb1", "sb3", "modules_access"], doc.enabled);
			frm.set_df_property("enabled", "read_only", 0);
		}

		if (frm.doc.name !== "Administrator") {
			frm.toggle_enable("email", frm.is_new());
		}
	},
	create_user_email: function (frm) {
		nts.call({
			method: "nts.core.doctype.user.user.has_email_account",
			args: {
				email: frm.doc.email,
			},
			callback: function (r) {
				if (!Array.isArray(r.message) || !r.message.length) {
					nts.route_options = {
						email_id: frm.doc.email,
						awaiting_password: 1,
						enable_incoming: 1,
					};
					nts.model.with_doctype("Email Account", function (doc) {
						doc = nts.model.get_new_doc("Email Account");
						nts.route_flags.linked_user = frm.doc.name;
						nts.route_flags.delete_user_from_locals = true;
						nts.set_route("Form", "Email Account", doc.name);
					});
				} else {
					nts.route_flags.create_user_account = frm.doc.name;
					nts.set_route("Form", "Email Account", r.message[0]["name"]);
				}
			},
		});
	},
	generate_keys: function (frm) {
		nts.call({
			method: "nts.core.doctype.user.user.generate_keys",
			args: {
				user: frm.doc.name,
			},
			callback: function (r) {
				if (r.message) {
					show_api_key_dialog(r.message.api_key, r.message.api_secret);
					frm.reload_doc();
				}
			},
		});
	},
	after_save: function (frm) {
		/**
		 * Checks whether the effective value has changed.
		 *
		 * @param {Array.<string>} - Tuple with new override, previous override,
		 *   and optionally fallback.
		 * @returns {boolean} - Whether the resulting value has effectively changed
		 */
		const has_effectively_changed = ([new_override, prev_override, fallback = undefined]) => {
			const prev_effective = prev_override || fallback;
			const new_effective = new_override || fallback;
			return new_override !== undefined && prev_effective !== new_effective;
		};

		const doc = frm.doc;
		const boot = nts.boot;
		const attr_tuples = [
			[doc.language, boot.user.language, boot.sysdefaults.language],
			[doc.time_zone, boot.time_zone.user, boot.time_zone.system],
			[doc.desk_theme, boot.user.desk_theme], // No system default.
		];

		if (doc.name === nts.session.user && attr_tuples.some(has_effectively_changed)) {
			nts.msgprint(__("Refreshing..."));
			window.location.reload();
		}
	},
	setup_impersonation: function (frm) {
		if (
			nts.session.user === "Administrator" &&
			frm.doc.name != "Administrator" &&
			!frm.is_new()
		) {
			frm.add_custom_button(__("Impersonate"), () => {
				if (frm.doc.restrict_ip) {
					nts.msgprint({
						message:
							"There's IP restriction for this user, you can not impersonate as this user.",
						title: "IP restriction is enabled",
					});
					return;
				}
				nts.prompt(
					[
						{
							fieldname: "reason",
							fieldtype: "Small Text",
							label: "Reason for impersonating",
							description: __("Note: This will be shared with user."),
							reqd: 1,
						},
					],
					(values) => {
						nts
							.xcall("nts.core.doctype.user.user.impersonate", {
								user: frm.doc.name,
								reason: values.reason,
							})
							.then(() => window.location.reload());
					},
					__("Impersonate as {0}", [frm.doc.name]),
					__("Confirm")
				);
			});
		}
	},
});

nts.ui.form.on("User Email", {
	email_account(frm, cdt, cdn) {
		let child_row = locals[cdt][cdn];
		nts.model.get_value(
			"Email Account",
			child_row.email_account,
			"auth_method",
			(value) => {
				child_row.used_oauth = value.auth_method === "OAuth";
				frm.refresh_field("user_emails", cdn, "used_oauth");
			}
		);
	},
});

nts.ui.form.on("User Role Profile", {
	role_profiles_add: function (frm) {
		if (frm.doc.role_profiles.length > 0) {
			frm.roles_editor.disable = 1;
			frm.call("populate_role_profile_roles").then(() => {
				frm.roles_editor.show();
			});
			$(".deselect-all, .select-all").prop("disabled", true);
		}
	},
	role_profiles_remove: function (frm) {
		if (frm.doc.role_profiles.length == 0) {
			frm.roles_editor.disable = 0;
			frm.roles_editor.show();
			$(".deselect-all, .select-all").prop("disabled", false);
		}
	},
});

function has_access_to_edit_user() {
	return has_common(nts.user_roles, get_roles_for_editing_user());
}

function get_roles_for_editing_user() {
	return (
		nts
			.get_meta("User")
			.permissions.filter((perm) => perm.permlevel >= 1 && perm.write)
			.map((perm) => perm.role) || ["System Manager"]
	);
}

function show_api_key_dialog(api_key, api_secret) {
	const dialog = new nts.ui.Dialog({
		title: __("API Keys"),
		fields: [
			{
				label: __("API Key"),
				fieldname: "api_key",
				fieldtype: "Code",
				read_only: 1,
				default: api_key,
			},
			{
				label: __("API Secret"),
				fieldname: "api_secret",
				fieldtype: "Code",
				read_only: 1,
				default: api_secret,
			},
		],
		size: "small",
		primary_action_label: __("Download"),
		primary_action: () => {
			nts.tools.downloadify(
				[
					["api_key", "api_secret"],
					[api_key, api_secret],
				],
				"System Manager",
				"nts_api_keys"
			);

			dialog.hide();
		},
		secondary_action_label: __("Copy token to clipboard"),
		secondary_action: () => {
			const token = `${api_key}:${api_secret}`;
			nts.utils.copy_to_clipboard(token);
			dialog.hide();
		},
	});

	dialog.show();
	dialog.show_message(
		__("Store the API secret securely. It won't be displayed again."),
		"yellow",
		1
	);
}

nts.ui.form.on("User Session Display", {
	sign_out(frm, doctype, name) {
		nts
			.xcall("nts.core.doctype.user.user.clear_session", { sid_hash: name })
			.then(() => frm.reload_doc());
	},
});
