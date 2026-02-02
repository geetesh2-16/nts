nts.provide("nts.ui.misc");
nts.ui.misc.about = function () {
	if (nts.ui.misc.about_dialog) {
		nts.ui.misc.about_dialog.show();
		return;
	}

	const dialog = new nts.ui.Dialog({ title: __("nts Framework") });

	$(dialog.body).html(
		`<div>
				<p>${__("Open Source Applications for the Web")}</p>

				<p>
					<i class='fa fa-globe fa-fw'></i>
					${__("Website")}:
					<a href='https://nts.io/' target='_blank'>https://nts.io/</a>
				</p>

				<p>
					<i class='fa fa-github fa-fw'></i>
					${__("Source Code")}:
					<a href='https://github.com/nts' target='_blank'>https://github.com/nts</a>
				</p>

				<p>
					<i class='fa fa-file-text fa-fw'></i>
					${__("nts Blog")}:
					<a href='https://nts.io/blog' target='_blank'>https://nts.io/blog</a>
				</p>

				<p>
					<i class='fa fa-users fa-fw'></i>
					${__("nts Forum")}:
					<a href='https://discuss.nts.io' target='_blank'>https://discuss.nts.io</a>
				</p>

				<p>
					<i class='fa fa-linkedin fa-fw'></i>
					${__("LinkedIn")}:
					<a href='https://linkedin.com/company/nts-tech' target='_blank'>https://linkedin.com/company/nts-tech</a>
				</p>

				<p>
					<svg xmlns="http://www.w3.org/2000/svg" width="18" height="14" fill="currentColor" class="bi bi-twitter-x" viewBox="0 0 18 16">
						<path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865z"/>
					</svg>
					X:
					<a href='https://x.com/ntstech' target='_blank'>https://x.com/ntstech</a>
				</p>

				<p>
					<i class='fa fa-youtube-play fa-fw'></i>
					${__("YouTube")}:
					<a href='https://www.youtube.com/@ntstech' target='_blank'>https://www.youtube.com/@ntstech</a>
				</p>

				<p>
					<i class='fa fa-instagram fa-fw'></i>
					${__("Instagram")}:
					<a href='https://www.instagram.com/ntstech' target='_blank'>https://www.instagram.com/ntstech</a>
				</p>

				<hr>

				<div class="d-flex align-items-center justify-content-between">
					<h4>${__("Installed Apps")}</h4>
					<button class="btn action-btn hidden" id="copy-apps-info"
					title="${__("Copy Apps Version")}"
					style="margin-bottom: var(--margin-md);">
						${nts.utils.icon("clipboard")}
					</button>
				</div>

				<div id='about-app-versions'>${__("Loading versions...")}</div>
				<p>
					<b>
						<a href="/attribution" target="_blank" class="text-muted">
							${__("Dependencies & Licenses")}
						</a>
					</b>
				</p>

				<hr>

				<p class='text-muted'>${__("&copy; nts Technologies Pvt. Ltd. and contributors")} </p>
			</div>`
	);

	nts.ui.misc.about_dialog = dialog;

	nts.ui.misc.about_dialog.on_page_show = function () {
		if (!nts.versions) {
			nts.call({
				method: "nts.utils.change_log.get_versions",
				callback: function (r) {
					show_versions(r.message);
				},
			});
		} else {
			show_versions(nts.versions);
		}
	};

	const show_versions = function (versions) {
		const $wrap = $("#about-app-versions").empty();
		let app = {};

		function get_version_text(app) {
			if (app.branch) {
				return `v${app.branch_version || app.version} (${app.branch})`;
			} else {
				return `v${app.version}`;
			}
		}

		for (const app_name in versions) {
			app = versions[app_name];
			const title = `${app_name}: ${app.branch_version || app.version}`;
			const text = `<p class='app-version' role='button' title='${title}'>
							<b>${app.title}:</b> ${get_version_text(app)}
						</p>`;
			$(text).appendTo($wrap);
		}

		nts.versions = versions;

		if (nts.versions) {
			$(dialog.body).find("#copy-apps-info").removeClass("hidden");
		}
	};

	const code_block = (snippet, lang = "") => "```" + lang + "\n" + snippet + "\n```";

	// Listener for copying installed apps info
	$(dialog.body).on("click", "#copy-apps-info", function () {
		if (!nts.versions) return;

		const versions = Object.entries(nts.versions).reduce((acc, [key, app]) => {
			acc[key] = app.branch_version || app.version;
			return acc;
		}, {});

		nts.utils.copy_to_clipboard(code_block(JSON.stringify(versions, null, "\t"), "json"));
	});

	// Listener for copy app version
	$(dialog.body).on("click", ".app-version", function () {
		const title = $(this).attr("title");
		if (title) {
			nts.utils.copy_to_clipboard(title);
		}
	});

	nts.ui.misc.about_dialog.show();
};
