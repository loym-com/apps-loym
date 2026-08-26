/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountReportLineCell } from "@account_reports/components/account_report/line_cell/line_cell";

let modifiedReportClick = false;

document.addEventListener(
    "click",
    ev => modifiedReportClick = ev.ctrlKey || ev.metaKey,
    true
);

patch(AccountReportLineCell.prototype, {
    async audit() {
        const newWindow = modifiedReportClick;
        modifiedReportClick = false;

        if (!newWindow) {
            return super.audit();
        }

        const doAction = this.action.doAction;

        this.action.doAction = (action, options = {}) =>
            doAction.call(this.action, action, { ...options, newWindow: true });

        try {
            return await super.audit();
        } finally {
            this.action.doAction = doAction;
        }
    },
});
