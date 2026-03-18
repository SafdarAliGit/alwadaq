frappe.query_reports["Employee Checkin Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
            reqd: 1,
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
        {
            fieldname: "designation",
            label: __("Designation"),
            fieldtype: "Link",
            options: "Designation",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data, default_formatter);

        // Highlight rows where check_out is missing
        if (column.fieldname === "check_out" && !data.check_out) {
            value = `<span style="color: red; font-weight: bold;">Missing</span>`;
        }

        // Highlight rows where check_in is missing
        if (column.fieldname === "check_in" && !data.check_in) {
            value = `<span style="color: orange; font-weight: bold;">Missing</span>`;
        }

        // Color working hours < 8 in orange
        if (
            column.fieldname === "working_hours" &&
            data.working_hours &&
            data.working_hours < 8
        ) {
            value = `<span style="color: orange;">${data.working_hours}</span>`;
        }

        return value;
    },
};