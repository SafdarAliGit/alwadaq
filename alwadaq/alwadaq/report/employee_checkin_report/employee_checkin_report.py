import frappe
from frappe import _
from datetime import timedelta


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "fieldname": "employee",
            "label": _("Employee ID"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 130,
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "fieldname": "designation",
            "label": _("Designation"),
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "fieldname": "shift",
            "label": _("Shift"),
            "fieldtype": "Data",
            "width": 130,
        },
        {
            "fieldname": "shift_in_time",
            "label": _("Shift Start"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "shift_out_time",
            "label": _("Shift End"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "check_in_time",
            "label": _("Check In"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "check_out_time",
            "label": _("Check Out"),
            "fieldtype": "Time",
            "width": 110,
        },
        {
            "fieldname": "working_hours",
            "label": _("Working Hours"),
            "fieldtype": "Float",
            "width": 130,
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100,
        },
    ]


def get_data(filters):
    filters = filters or {}

    # ── 1. Fetch all matching employees (respects employee/dept/desig filters)
    emp_conditions = _get_employee_conditions(filters)
    emp_rows = frappe.db.sql(
        """
        SELECT
            e.name          AS employee,
            e.employee_name,
            e.designation
        FROM
            `tabEmployee` e
        WHERE
            e.status = 'Active'
            {emp_conditions}
        ORDER BY
            e.name ASC
        """.format(emp_conditions=emp_conditions),
        filters,
        as_dict=True,
    )

    if not emp_rows:
        return []

    employee_ids = [r["employee"] for r in emp_rows]
    emp_map = {r["employee"]: r for r in emp_rows}

    # ── 2. Fetch checkin aggregates using ROW_NUMBER to pick 1st and 2nd punch
    #       regardless of log_type value.
    #       ranked CTE assigns rank per (employee, date) ordered by time ASC.
    #       Outer query picks rank=1 as check-in, rank=2 as check-out.
    checkin_conditions = _get_checkin_conditions(filters, employee_ids)

    checkin_rows = frappe.db.sql(
        """
        SELECT
            ranked.employee,
            ranked.date,
            MAX(ranked.shift)                                       AS shift,
            MAX(st.start_time)                                      AS shift_in_time,
            MAX(st.end_time)                                        AS shift_out_time,
            MAX(CASE WHEN ranked.rn = 1 THEN ranked.time END)       AS check_in_dt,
            MAX(CASE WHEN ranked.rn = 2 THEN ranked.time END)       AS check_out_dt,
            ROUND(
                TIMESTAMPDIFF(
                    MINUTE,
                    MAX(CASE WHEN ranked.rn = 1 THEN ranked.time END),
                    MAX(CASE WHEN ranked.rn = 2 THEN ranked.time END)
                ) / 60.0,
                2
            )                                                       AS working_hours
        FROM (
            SELECT
                ec.employee,
                DATE(ec.time)   AS date,
                ec.time,
                ec.shift,
                ROW_NUMBER() OVER (
                    PARTITION BY ec.employee, DATE(ec.time)
                    ORDER BY ec.time ASC
                )               AS rn
            FROM
                `tabEmployee Checkin` ec
            WHERE
                1=1 {checkin_conditions}
        ) AS ranked
        LEFT JOIN
            `tabShift Type` st ON st.name = ranked.shift
        GROUP BY
            ranked.employee, ranked.date
        """.format(checkin_conditions=checkin_conditions),
        filters,
        as_dict=True,
    )

    # ── 3. Build result rows ──────────────────────────────────────────────────
    # - Employees WITH checkins  → one row per (employee, date) they appeared
    # - Employees WITHOUT any checkin in the range → single row, no date
    result_present = []
    result_absent  = []

    # Track which employees had at least one checkin in the range
    employees_with_checkin = set(row["employee"] for row in checkin_rows)

    # Present rows — iterate over actual checkin records only
    for ci in checkin_rows:
        eid = ci["employee"]
        emp = emp_map.get(eid, {})
        result_present.append({
            "date":          ci.get("date"),
            "employee":      eid,
            "employee_name": emp.get("employee_name"),
            "designation":   emp.get("designation"),
            "shift":         ci.get("shift"),
            "shift_in_time": _td_to_time_str(ci.get("shift_in_time")),
            "shift_out_time":_td_to_time_str(ci.get("shift_out_time")),
            "check_in_time": _dt_to_time_str(ci.get("check_in_dt")),
            "check_out_time":_dt_to_time_str(ci.get("check_out_dt")),
            "working_hours": ci.get("working_hours"),
            "status":        "Present",
        })

    # Absent rows — one per employee who never appeared in checkins
    for emp in emp_rows:
        eid = emp["employee"]
        if eid not in employees_with_checkin:
            result_absent.append({
                "date":          None,
                "employee":      eid,
                "employee_name": emp.get("employee_name"),
                "designation":   emp.get("designation"),
                "shift":         None,
                "shift_in_time": None,
                "shift_out_time":None,
                "check_in_time": None,
                "check_out_time":None,
                "working_hours": None,
                "status":        "Absent",
            })

    # Sort present rows: most-recent date first, then employee ascending
    result_present.sort(key=lambda r: (r["date"], r["employee"]), reverse=False)
    result_present.sort(key=lambda r: r["date"], reverse=True)

    # Absent rows sorted by employee name
    result_absent.sort(key=lambda r: r["employee"])

    # Present rows first, then absent at the bottom
    return result_present + result_absent


# ── helpers ───────────────────────────────────────────────────────────────────

def _dt_to_time_str(dt):
    """datetime → 'HH:MM:SS'  (or None if missing)"""
    if not dt:
        return None
    try:
        return dt.strftime("%H:%M:%S")
    except AttributeError:
        return str(dt)


def _td_to_time_str(td):
    """timedelta → 'HH:MM:SS'  (MariaDB returns TIME columns as timedelta)"""
    if td is None:
        return None
    if isinstance(td, timedelta):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return str(td)


def _get_employee_conditions(filters):
    """WHERE clauses that apply to the Employee table directly."""
    conditions = ""
    if filters.get("employee"):
        conditions += " AND e.name = %(employee)s"
    if filters.get("department"):
        conditions += " AND e.department = %(department)s"
    if filters.get("designation"):
        conditions += " AND e.designation = %(designation)s"
    return conditions


def _get_checkin_conditions(filters, employee_ids):
    """
    WHERE clauses for the checkin query.
    employee_ids list is injected directly (safe — they are internal PK values
    fetched from our own employee query above, never from raw user input).
    """
    # Always restrict to the employees we already resolved
    ids_placeholder = ", ".join(
        "'{}'".format(eid.replace("'", "''")) for eid in employee_ids
    )
    conditions = " AND ec.employee IN ({})".format(ids_placeholder)

    if filters.get("shift"):
        conditions += " AND ec.shift = %(shift)s"

    if filters.get("from_date"):
        conditions += " AND DATE(ec.time) >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND DATE(ec.time) <= %(to_date)s"

    return conditions