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
        {
            fieldname: "shift",
            label: __("Shift"),
            fieldtype: "Link",
            options: "Shift Type",
        },
    ],

    formatter: function (value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data, default_formatter);

        // IN status column — green tick if punched, red cross if missing
        if (column.fieldname === "in_status") {
            return parseInt(data.in_status) === 1
                ? `<span style="color: green; font-size: 14px; font-weight: bold;">&#10003;</span>`
                : `<span style="color: red;   font-size: 14px; font-weight: bold;">&#10007;</span>`;
        }

        // OUT status column — green tick if punched, red cross if missing
        if (column.fieldname === "out_status") {
            return parseInt(data.out_status) === 1
                ? `<span style="color: green; font-size: 14px; font-weight: bold;">&#10003;</span>`
                : `<span style="color: red;   font-size: 14px; font-weight: bold;">&#10007;</span>`;
        }

        // Working hours — only show N/A when the value is genuinely null/undefined
        if (column.fieldname === "working_hours") {
            const wh = parseFloat(data.working_hours);
            if (isNaN(wh) || data.working_hours === null || data.working_hours === undefined) {
                return `<span style="color: red;">N/A</span>`;
            }
            if (wh < 8) {
                return `<span style="color: orange;">${wh.toFixed(2)}</span>`;
            }
            return `<span style="color: green;">${wh.toFixed(2)}</span>`;
        }

        return value;
    },
};