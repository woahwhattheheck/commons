# Recorded result

Status: `RESEARCH_DELIVERY_NOT_CONNECTED`

The included workflow reconciles three invoice lines against three PO lines:

- two lines match exactly and become review-ready accounting export rows totaling $74.00;
- one line invoices 3 units against 2 ordered units and becomes an unsent exception draft;
- all three originals are linked by SHA-256 and source line;
- zero drafts are sent and zero accounting rows are posted.

This is deterministic fixture evidence, not customer activity, acceptance, revenue, or payment. No external accounting or messaging system was contacted.
