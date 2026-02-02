// Copyright (c) 2019, nts Technologies and contributors
// For license information, please see license.txt

nts.ui.form.on("Server Script", {
	setup: function (frm) {
		frm.trigger("setup_help");
	},
	refresh: function (frm) {
		if (frm.doc.script_type != "Scheduler Event") {
			frm.dashboard.hide();
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("Compare Versions"), () => {
				new nts.ui.DiffView("Server Script", "script", frm.doc.name);
			});
		}

		setTimeout(() => {
			nts
				.call("nts.core.doctype.server_script.server_script.get_autocompletion_items")
				.then((r) => r.message)
				.then((items) => {
					frm.set_df_property("script", "autocompletions", items);
				});
		}, 100);

		frm.trigger("check_safe_exec");
	},

	check_safe_exec(frm) {
		nts.xcall("nts.core.doctype.server_script.server_script.enabled").then((enabled) => {
			if (enabled === false) {
				let docs_link =
					"https://ntsframework.com/docs/user/en/desk/scripting/server-script";
				let docs = `<a href=${docs_link}>${__("Official Documentation")}</a>`;

				frm.dashboard.clear_comment();
				let msg = __("Server Scripts feature is not available on this site.") + " ";
				msg += __("To enable server scripts, read the {0}.", [docs]);
				frm.dashboard.add_comment(msg, "yellow", true);
			}
		});
	},

	setup_help(frm) {
		const help_field = frm.get_field("help_html");
		help_field.html(`
<h4>DocType Event</h4>
<p>Add logic for standard doctype events like Before Insert, After Submit, etc.</p>
<pre><code class="language-python">
# set property
if "test" in doc.description:
	doc.status = 'Closed'

# validate
if "validate" in doc.description:
	raise nts.ValidationError

# auto create another document
if doc.allocated_to:
	nts.get_doc(dict(
		doctype = 'ToDo'
		owner = doc.allocated_to,
		description = doc.subject
	)).insert()
</code></pre>

<h5>Payment processing</h5>
<p>Payment processing events have a special state. See the <a href="https://github.com/nts/payments/blob/develop/payments/controllers/payment_controller.py">PaymentController in nts Payments</a> for details.</p>
<pre><code class="language-python">
# retreive payment session state
ps = doc.flags.payment_session

if ps.is_success:
	if ps.changed: # could be an idempotent run
		doc.set_as_paid()
	# custom process return values
	doc.flags.payment_session.result = {
		"message": "Thank you for your payment",
		"action": {
			"href": "https://shop.example.com",
			"label": "Return to shop"
		}
	}
if ps.is_pre_authorized:
	if ps.changed: # could be an idempotent run
		...
if ps.is_processing:
	if ps.changed: # could be an idempotent run
		...
if ps.is_declined:
	if ps.changed: # could be an idempotent run
		...
</code></pre>

<p>The <i>On Payment Failed</i> (<code>on_payment_failed</code>) event only transports the error message which the controller implementation had extracted from the transaction.</p>

<pre><code class="language-python">
msg = doc.flags.payment_failure_message
doc.my_failure_message_field = msg
</code></pre>

<hr>

<h4>API Call</h4>
<p>Respond to <code>/api/method/&lt;method-name&gt;</code> calls, just like whitelisted methods</p>
<pre><code class="language-python">
# respond to API

if nts.form_dict.message == "ping":
	nts.response['message'] = "pong"
else:
	nts.response['message'] = "ok"
</code></pre>

<hr>

<h4>Permission Query</h4>
<p>Add conditions to the where clause of list queries.</p>
<p>Generate dynamic conditions and set it in the conditions variable:</p>

<pre><code class="language-python">
tenant_id = nts.db.get_value(...) # -> 2
conditions = f'tenant_id = {tenant_id}'
</code></pre>

<p>The resulting select query is:</p>

<pre><code class="language-sql">
select name from \`tabPerson\`
where tenant_id = 2
order by creation desc
</code></pre>

<hr>

<h4>Workflow Task</h4>
<p>Execute when a particular <a href="/desk/workflow-action-master">Workflow Action Master</a> is executed.</p>
<p>Gets the document which the action is being applied on in the <code>doc</code> variable.</p>
<pre><code class="language-python">
# create a customer with the same name as the given document
customer = nts.new_doc("Customer")
customer.customer_name = doc.first_name + " " + doc.last_name # we get this doc from the workflow action
customer.customer_type = "Company"
customer.save()
</code></pre>`);
		nts.utils.highlight_pre(help_field.$wrapper);
	},
});
