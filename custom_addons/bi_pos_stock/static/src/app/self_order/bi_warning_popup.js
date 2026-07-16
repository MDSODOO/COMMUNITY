/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class BiWarningPopup extends Component {
    static template = "bi_pos_restrict_stock.BiWarningPopup";
    static defaultProps = {
        confirmText: _t("Ok"),
        cancelKey: false,
        body: "",
    };
    // FIXED: Removed dead-code order() method that:
    //   1. Called addToCart() from a denial popup (contradictory).
    //   2. Mutated product.qty_available / virtual_available — fields removed in
    //      the refactoring. Neither field exists on the model anymore.
    // The "Ok" button in the template calls props.close() directly, so order()
    // was never triggered. Removed to avoid future confusion.
}
