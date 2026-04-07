# Enhanced Fee Deposit System - Documentation

## Overview
The fee deposit system has been completely enhanced to support professional fee management with auto-calculation, month selection, previous due balance tracking, transportation fees, and concession management.

## Features Implemented

### 1. **Month-Based Fee Calculation** ✅
- Users can select which month's fee they want to collect
- System automatically calculates fees based on the selected month and student's class
- Supports all 12 months: January to December

### 2. **Auto-Calculate Fee Breakdown** ✅
- Automatically fetches fee particulars (Tuition, Lab, Library, etc.) from fee slabs
- Displays breakdown by particular with original amount, discount, and final amount
- Shows detailed fee structure for transparency

### 3. **Transportation Fee Auto-Add** ✅
- Automatically includes transportation fee if student:
  - Has `transport_required = True`
  - Is assigned to a `transport_route`
- Transportation fee is calculated based on the route's fare amount
- Displayed separately in breakdown
- Works based on student's village/route assignment

### 4. **Previous Due Balance Tracking** ✅
- Calculates any outstanding balance from previous months
- Shows previous due as a separate section before total
- Formula: `Total Amount Due = Current Month Fee + Previous Due - Concession`
- Prevent revenue leakage by ensuring old dues are collected

### 5. **Concession/Discount Management** ✅
- Field to enter concession amount (fixed amount discount)
- Textarea to record reason for concession (merit, hardship, scholarship, etc.)
- Concession deducted from total before balance calculation
- Audit trail preserved in remarks

### 6. **Detailed Balance Calculation** ✅
- Shows remaining balance after payment
- Formula: `Balance = (Current Fee + Previous Due - Concession) - Paid Amount`
- Auto-filled with total amount due
- Real-time recalculation as user enters paid amount

### 7. **Payment Details Tracking** ✅
New fields added to Fee model:
- `fee_month` - Month for which fee is being collected (jan, feb, ... dec)
- `payment_mode` - Cash, Cheque, Online, Card, Other
- `reference_number` - Check/Transaction number for reference
- `previous_due_balance` - Tracked automatically
- `concession_amount` - Discount given
- `concession_remarks` - Reason for discount
- `remarks` - Additional notes about payment

## Database Schema Changes

### Fee Model Enhancement
```python
class Fee(models.Model):
    student = ForeignKey(Student)
    total_fee = DecimalField()              # Current month fee
    paid_fee = DecimalField()               # Amount paid
    due_fee = DecimalField()                # Remaining balance (auto-calculated)
    previous_due_balance = DecimalField()   # ✨ NEW
    concession_amount = DecimalField()      # ✨ NEW
    concession_remarks = TextField()        # ✨ NEW
    fee_month = CharField(month choices)    # ✨ NEW (jan-dec)
    payment_mode = CharField()              # ✨ NEW
    reference_number = CharField()          # ✨ NEW
    remarks = TextField()                   # ✨ NEW
    date = DateField()
    session = ForeignKey(AcademicSession)
```

## API Endpoints

### 1. Calculate Student Fees
**GET** `/fee/api/calculate-student-fees/`

**Parameters:**
- `student_id` (required) - ID of the student
- `fee_month` (required) - Month code (jan, feb, mar, ... dec)

**Response:**
```json
{
    "success": true,
    "student": {
        "id": 1,
        "name": "John Doe",
        "admission_number": "RLCS001",
        "student_class": "Class 10",
        "section": "A",
        "roll_no": 1,
        "transport_route": "Route A",
        "transport_village": "Village XYZ"
    },
    "fee_breakdown": [
        {
            "particular_name": "Tuition Fee",
            "original_amount": 5000,
            "discount_amount": 500,
            "final_amount": 4500,
            "particular_id": 1
        },
        {
            "particular_name": "Transport Fee",
            "original_amount": 1000,
            "discount_amount": 0,
            "final_amount": 1000,
            "particular_id": null
        }
    ],
    "current_month_fee": 5500,
    "previous_due_balance": 2000,
    "total_amount_due": 7500,
    "transport_fee": 1000,
    "fee_month": "jan",
    "fee_month_display": "January"
}
```

### 2. Save Fee Deposit
**POST** `/fee/deposit/save/`

**Parameters:**
- `student_id` - Student ID
- `total_fee` - Current month fee amount
- `paid_amount` - Amount being paid
- `payment_date` - Date of payment
- `fee_month` - Month code (jan-dec)
- `concession_amount` - Discount amount (optional)
- `concession_remarks` - Reason for discount (optional)
- `payment_mode` - Payment method (optional)
- `reference_number` - Transaction reference (optional)
- `remarks` - Additional notes (optional)

**Response:**
```json
{
    "success": true,
    "message": "Fee deposit saved successfully",
    "fee_id": 123,
    "receipt_data": {
        "student_name": "John Doe",
        "admission_number": "RLCS001",
        "class": "Class 10",
        "section": "A",
        "total_fee": 5500,
        "previous_due": 2000,
        "concession": 500,
        "paid_amount": 7000,
        "balance": 0,
        "fee_month": "jan",
        "payment_date": "2025-01-15",
        "payment_mode": "cash"
    }
}
```

## Usage Workflow

### Step 1: Search Student
1. Navigate to `/fee/deposit/`
2. Choose search method:
   - **By Admission Number**: Enter RLCS001, RLCS002, etc.
   - **By Class & Section**: Select class and section from dropdowns
3. Click "Search Student"
4. Click on student card to select

### Step 2: Select Month & Calculate Fees
1. After student is selected, "Fee Details" section appears
2. Select month from dropdown (January - December)
3. System automatically calculates:
   - Current month's fee breakdown
   - Previous due balance (if any)
   - Transportation fee (if applicable)
   - Total amount due
4. Review fee breakdown details

### Step 3: Enter Payment Details
1. Select payment mode (Cash, Cheque, Online, Card)
2. Enter or auto-fill paid amount
3. Review remaining balance
4. Click "Complete Fee Deposit" (or similar button)

### Step 4: Add Concession (Optional)
1. In deposit form, enter concession amount if giving discount
2. Select reason: Merit scholarship, Financial hardship, etc.
3. This deducts from total before final balance

### Step 5: Complete Payment
1. Verify payment date (auto-filled with today's date)
2. Select payment mode again in form
3. Enter reference number if applicable (check number, transaction ID)
4. Add remarks if needed
5. Click "Save Deposit & Print Receipt"

### Step 6: Receipt Generated
- System creates fee record with all details
- Shows receipt summary with:
  - Student name and admission number
  - Total fee, previous due, concession
  - Amount paid and remaining balance
  - Payment method and date

## Important Calculations

### Total Amount Due Formula:
```
Total Due = (Current Month Fee + Previous Due Balance) - Concession
```

### Balance After Payment:
```
Remaining Balance = Total Amount Due - Paid Amount
```

### Previous Due Balance:
```
Previous Due = Sum of all (due_fee) from Fee records where fee_month != current_month and due_fee > 0
```

## Example Scenario

**Student:** Raj Kumar (Class 10A, Admission: RLCS001)
**Scenario:** Collecting January fee with previous due

1. Current Month Fee: ₹5,000 (Tuition)
2. Transportation Fee: ₹500 (Route A, Village XYZ)
3. Subtotal: ₹5,500

4. Previous Due Balance: ₹2,000 (from December unpaid)
5. Total Amount Due: ₹7,500

6. Concession Given: ₹500 (Merit scholarship)
7. Amount After Concession: ₹7,000

8. Paid Amount: ₹7,000
9. Remaining Balance: ₹0 (Fully Paid)

**Record Created:**
```
Fee Record:
- Student: Raj Kumar (RLCS001)
- Total Fee: ₹5,500 (current month)
- Previous Due: ₹2,000
- Concession: ₹500
- Paid: ₹7,000
- Balance: ₹0
- Month: January (jan)
- Payment Mode: Cash
- Date: 2025-01-15
```

## Benefits

1. **Accurate Tracking**: No revenue loss - previous dues automatically tracked
2. **Transparent Breakdown**: Students see exactly what they're paying for
3. **Flexible Discounts**: Support various concession types with audit trail
4. **Month-Wise Management**: Easy to track which months are paid
5. **Transport Integration**: Automatic calculation based on village/route
6. **Audit Trail**: All details including payment reference stored
7. **Batch Payment Support**: Can collect multiple months' dues in single transaction
8. **Balance Reporting**: Clear visibility of outstanding balance

## Admin Panel Features
1. View/Edit fee records with all new fields
2. Filter fees by month, payment mode, student class
3. Generate reports showing:
   - Monthly revenue by class
   - Outstanding dues by student
   - Concession analysis
   - Collection rate

## Migration Information
- New migration: `students/migrations/0010_*` applied
- No data loss - existing fee records remain intact
- New fields have default values for backward compatibility

## API Testing

### Test Fee Calculation:
```bash
curl "http://localhost:8000/fee/api/calculate-student-fees/?student_id=1&fee_month=jan"
```

### Test Fee Deposit Save:
```bash
curl -X POST http://localhost:8000/fee/deposit/save/ \
  -H "X-CSRFToken: <token>" \
  -d "student_id=1&total_fee=5500&paid_amount=5500&payment_date=2025-01-15&fee_month=jan&payment_mode=cash"
```

## Troubleshooting

### Issue: No fee breakdown showing
**Solution**: Ensure FeeAmountSlab exists for student's class and selected month in admin panel

### Issue: Transportation fee not showing
**Solution**: Verify student has:
- `transport_required = True`
- A transport_route assigned

### Issue: Previous due not calculating
**Solution**: System automatically calculates from previous Fee records with due_fee > 0

### Issue: Concession not deducting
**Solution**: Ensure you enter concession amount in deposit form before saving

## Support & Contact
For issues or enhancements related to fee deposit:
1. Check FeeAmountSlab setup in admin
2. Verify student transport settings
3. Review previous fee records for due balance tracking
4. Check browser console for JavaScript errors

---
**Last Updated:** 2025-01-15
**System Version:** Enhanced Fee Deposit v1.0
**Status:** ✅ Production Ready
