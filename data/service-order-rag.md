# Service Order Section

**Module:** Service Order Section\
**Description:** Order investigations, procedures, and packages from the
consultation screen\
**Version:** 1.0\
**Last Updated:** Apr 2026

## Overview

The Service Order Section is embedded in the patient consultation
screen. It allows clinicians and support staff to order Lab, Radiology,
Procedure, Vaccine, Medicine, and Package services for a patient --- all
from one place.

### What you can do here

-   Order any service type using **Search**, **Packages**, or **Order
    Sets**.
-   Use **Favorites** for quick access to frequently ordered services.
-   View real-time **Insurance Rule Alerts** including hard blocks, soft
    warnings, and information notes in Insurance mode.
-   **Repeat** a previously ordered service with a note and custom
    quantity.
-   View **Lab Reports** and **Radiology PDF Reports** for completed
    orders.
-   Delete eligible orders or remove an entire package in one step.

### Note: Read-Only Mode

When a consultation is closed or locked, the **Order Services** button,
delete icons, and Repeat buttons are hidden. Orders can still be viewed
and completed reports can still be opened.

------------------------------------------------------------------------

## Who Uses This Section

  -----------------------------------------------------------------------
  Role                                Primary Activities
  ----------------------------------- -----------------------------------
  Doctor / Clinician                  Orders services, reviews insurance
                                      alerts, views completed reports

  Nurse / Clinical Support            Places orders on behalf of the
                                      doctor, monitors status

  Receptionist / Admin                Views orders in read-only mode;
                                      assists with package selection

  Insurance Coordinator               Monitors authorization status and
                                      pre-auth requirements per row
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Ordering Services

Click **+ Order Services** at the top-right of the panel to open the
Order Modal.

The modal has three tabs:

  -----------------------------------------------------------------------
  Tab                     Use When                How It Works
  ----------------------- ----------------------- -----------------------
  Search                  You know the service    Type to search; filter
                          name or CPT code        by All, Lab, Radiology,
                                                  or Procedure. Click +
                                                  to add to the cart.

  Packages                Patient needs a bundled Expand a package to
                          package of services     preview included
                                                  services, then click
                                                  Select Package.

  Order Sets              You want a              Search order sets,
                          pre-configured group of expand to preview, and
                          services                click Add to Order. All
                                                  services in the set are
                                                  added to the cart.
  -----------------------------------------------------------------------

### Using Favorites

1.  On the **Search** tab, click the **Favorites** button.
2.  Your saved folders appear. Click a folder to expand it.
3.  Click any service in the folder to add it directly to the cart.

### Confirming the Order

1.  Review the cart in the right panel. Verify service names, types, and
    quantities.
2.  Click **Confirm Order**.
3.  Orders are created and immediately appear in the relevant table.
4.  Insurance rules are re-evaluated automatically in Insurance mode.

### Tip: Duplicate Detection

If a service has already been ordered for this visit, a warning badge
appears next to it in the search results. You can still add it. Use the
**Repeat** action on the original row if you specifically want to create
an audit-linked repeat order.

### Warning: Pre-Approval Limit

In Insurance mode, if the patient has a pre-approval limit and the order
would exceed it, a confirmation dialog appears before saving. You can
acknowledge and continue or cancel to adjust the selection.

------------------------------------------------------------------------

## Reading the Order Tables

Orders are grouped into three separate tables. Each table can be sorted
independently.

  -----------------------------------------------------------------------
  Table                               Contains
  ----------------------------------- -----------------------------------
  Investigations (Lab & Radiology)    All Lab and Radiology orders

  Procedures & Other Services         Procedures, Consultations,
                                      Vaccines, Medicines, Other

  Packages                            Orders that belong to a patient
                                      package
  -----------------------------------------------------------------------

### Column Reference

  -----------------------------------------------------------------------
  Column                              Description
  ----------------------------------- -----------------------------------
  \#                                  Sequential row number within the
                                      table

  CPT Code                            Standard CPT billing code

  Internal Code                       Facility's own service code

  Service                             Service name plus Package, Order
                                      Set, Repeated, or Insurance Alert
                                      badges

  Type                                Lab, Radiology, Procedure,
                                      Consultation, Vaccine, or Medicine

  Qty                                 Quantity ordered

  Price                               Total price for this order line. It
                                      may be hidden for the Doctor role.

  Co-Pay                              Patient co-pay amount shown in
                                      Insurance or Corporate mode only

  Ordered                             Who placed the order and the
                                      date/time

  Status                              Current order lifecycle status

  Coverage                            Cash, Covered, or Pre-Auth Required

  Auth Status                         Authorization outcome with
                                      authorization number in Insurance
                                      mode

  Actions                             Delete, View/Download Report, and
                                      Repeat actions
  -----------------------------------------------------------------------

### Service Name Badges

-   **Package Name** --- service belongs to a package.
-   **Order Set** --- service was added through an Order Set.
-   **Repeated** --- service has been repeated.

### Tip: Package Price Rows

For services that are part of a package, the Price cell shows
**Included** and the Co-Pay cell shows **N/A** instead of numeric
values.

------------------------------------------------------------------------

## Sorting the Table

Each of the three order tables supports independent column-level
sorting.

-   ↕ --- Unsorted
-   ↑ --- Ascending
-   ↓ --- Descending

  Column    Sort Behaviour
  --------- -------------------------------------------
  Service   Alphabetical by service or test name
  Type      Alphabetical by service type
  Ordered   Chronological by order creation date/time
  Status    Alphabetical by status label

### How to Sort

1.  Click a sortable column header. The first click sorts ascending.
2.  Click again to switch to descending.
3.  Sorting is independent per table.

------------------------------------------------------------------------

## Status and Coverage Reference

### Order Status

  -----------------------------------------------------------------------
  Status                              Meaning
  ----------------------------------- -----------------------------------
  Pending                             Order placed; not yet started

  PreAuth Pending                     Pre-authorization requested from
                                      insurer; awaiting response

  In Progress                         Service is being performed

  Completed                           Service fully completed; results or
                                      report available

  Cancelled                           Order was cancelled
  -----------------------------------------------------------------------

### Coverage Types

-   **Cash** --- Patient pays the full cash price.
-   **Covered** --- Insurer or Corporate covers the service; patient
    pays co-pay where applicable.
-   **Pre-Auth Required** --- Insurer prior authorization is required
    before the service can be performed or invoiced.

### Authorization Status

  -----------------------------------------------------------------------
  Authorization Status                Meaning
  ----------------------------------- -----------------------------------
  Approved                            Insurer approved the service for
                                      billing

  Partially Approved                  Approved at a different quantity or
                                      amount than requested

  Denied                              Insurer declined coverage; denial
                                      code and rejection reason may
                                      appear

  Empty                               No authorization request submitted
                                      yet
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## Repeating a Service

The **Repeat** action creates a new linked order for the same service.

### How to Repeat a Service

1.  Locate the order and click **Repeat**.
2.  Confirm the service name and code.
3.  Set the quantity.
4.  Optionally enter a note, such as "Repeat after 48 hours".
5.  Click **Repeat Service**.

### Tip: Repeated Badge

After repeating, the original order shows a **Repeated** badge. Hover
over the badge to read repeat notes. The new order is a standard Pending
order.

------------------------------------------------------------------------

## Removing Orders

Click the trash icon in the Actions column to delete an eligible order.

  Blocking Condition           Result
  ---------------------------- ----------------------------
  Order is Completed           Cannot delete
  Order has been billed        Cannot delete
  Order is part of a Package   Cannot delete individually

### Note

An eligible Pending or PreAuth Pending order that is not billed and is
not part of a package is deleted immediately without a confirmation
prompt.

------------------------------------------------------------------------

## Deleting a Package

An entire package can be deleted only when all services are Pending or
PreAuth Pending and none have been billed.

### How to Delete a Package

1.  Find the package badge in the Service column.
2.  Click the trash icon inside the package badge.
3.  Review the package name and number of services in the confirmation
    modal.
4.  Click **Delete Package**.

### Warning

If even one order in the package is Completed or invoiced, the package
delete action is unavailable.

------------------------------------------------------------------------

## Viewing Lab Reports

For Completed Lab orders, a **View Lab Report** action appears.

1.  Locate the completed Lab order in Investigations.
2.  Click the View Lab Report icon.
3.  The Lab Report Preview Modal opens for the patient and visit.
4.  The user remains on the consultation screen.

------------------------------------------------------------------------

## Radiology PDF Reports

For Completed Radiology orders, users can view or download the PDF
report.

  Action         Behaviour
  -------------- ---------------------------------------
  View PDF       Opens the PDF in a full-screen viewer
  Download PDF   Downloads the PDF directly

If a PDF has not yet been generated, the system requests generation and
then opens or downloads the newly created report.

------------------------------------------------------------------------

## Insurance Rule Alerts

Insurance Rule Alerts are available only in **Insurance mode**.

  -----------------------------------------------------------------------
  Alert Type                          Meaning
  ----------------------------------- -----------------------------------
  Hard Block                          Strict rule violation requiring
                                      review and doctor override to
                                      proceed

  Soft Warning                        Potential issue that should be
                                      reviewed

  Info                                Coding, documentation, or coverage
                                      guidance
  -----------------------------------------------------------------------

Each alert may contain the domain, message, suggested action, source
reference, affected CPT codes, and confidence score.

### Doctor Override

1.  Click **Override** on the Hard Block alert.
2.  Enter the clinical justification.
3.  Click **Confirm Override**.
4.  The override and reason are recorded in the audit trail.

### Warning

A doctor override does not guarantee insurer payment. It records the
clinician's decision to proceed.

------------------------------------------------------------------------

## Price Visibility

Price visibility depends on the logged-in user's role.

  ---------------------------------------------------------------------------------
  Role                                Price Visibility
  ----------------------------------- ---------------------------------------------
  Doctor                              Hidden by default unless
                                      `REACT_APP_DOCTOR_CAREBOARD_SHOWPRICE=true`

  All other roles                     Always visible
  ---------------------------------------------------------------------------------

The Co-Pay column is hidden in Cash mode.

------------------------------------------------------------------------

## Quick Reference

  Action                   Purpose
  ------------------------ -----------------------------------------------
  \+ Order Services        Open the Order Modal
  Repeat                   Create a linked repeat order
  Delete                   Delete an eligible Pending/unbilled order
  Delete Package           Remove an eligible package and all its orders
  View Lab Report          Open a completed Lab report
  View Radiology PDF       Open a completed Radiology PDF
  Download Radiology PDF   Download the completed report
  Override                 Record a clinical override for a Hard Block

### Delete and Repeat Eligibility

  Status            Can Delete?          Can Repeat?
  ----------------- -------------------- -------------
  Pending           Yes, if not billed   Yes
  PreAuth Pending   Yes, if not billed   Yes
  In Progress       No                   Yes
  Completed         No                   Yes
  Cancelled         No                   Yes
