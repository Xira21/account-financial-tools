The module in NOT compatible with the standard account_asset module.

## Modify the value of a running asset

The value of a running asset can be increased or decreased with the
**Modify Value** button of the asset form (Accounting Manager rights).
The wizard asks for the date of the change, a reason and the new net
book value of the asset at that date, and it shows a summary of what
will be posted.

All the depreciation lines before the date of the change must be posted.
The asset is first depreciated with its current plan until the day
before the change: the depreciation line of the current period is split
and its first part is posted.

### Value decrease

- A depreciation entry is posted for the decrease, on the date of the
  change, with the depreciation accounts of the asset profile. It is
  shown in the depreciation board with its own description.
- The new value is spread over all the pending depreciation lines, in
  proportion to the depreciation plan, so the shape of the plan is kept
  (also for degressive methods). Recomputing the depreciation board
  keeps this spread.
- The new value cannot be lower than the salvage value. A decrease to
  zero (or to the salvage value) closes the asset.
- On an asset with value increases, a decrease only changes that asset;
  the wizard shows the total value for information.

### Value increase

- The asset keeps its depreciation plan, and a new asset is created for
  the increase: it starts on the date of the change, it has the same
  profile and depreciation method, and it ends on the same date as the
  increased asset.
- Its acquisition entry is posted on the asset account against the
  **Counterpart Account** chosen in the wizard (for example, the
  supplier or bank account, or the work performed by the company).
- Use it only for improvements or extensions that increase the
  capacity, productivity or useful life of the asset. Repairs are
  recorded as an expense, and an addition with a different useful life
  is registered as a separate asset.

The increased asset shows its value increases with the **Increases**
button, with their gross value and the total book value. Each value
increase shows its parent with the **Parent Asset** button.

### Value increase assets

- Their value cannot be increased: increases are made from the parent
  asset.
- Their depreciation method, duration and profile are managed from the
  parent asset: they cannot be changed nor set to draft. When the parent
  asset is set to draft, changed and recomputed, its running value
  increases follow its method, period and end date, without changing
  their posted depreciation lines.
- Their value can be decreased, and they are removed separately with the
  usual removal wizard.
- The parent asset can only be removed after its value increases have
  been removed, and an asset with value increases cannot be deleted.

### Checks and history

- The date of the change cannot be before the start date of the asset,
  and its entries (including the depreciation of the day before the
  change) cannot be in a locked period.
- Each change is logged in the chatter of the asset, with the values
  before and after the change, the reason and links to the entries. A
  value increase is also logged in the chatter of the new asset.

### Undoing a value modification

Deleting or reversing the journal entry of a value modification does not
undo the modification, as in Odoo Enterprise: for a decrease or the
prorata depreciation, the amount is posted again later; for an increase,
the increase asset keeps running. To correct a modification, make the
opposite one (an increase to cancel a decrease, or a decrease on the
increase asset).
