# Personnel and Payment System — Ubiquitous Language

## Person

An individual or business engaged by Opus Formosa. All people in the initial scope are independent contractors, not employees.

One person may have multiple searchable names. For example, Sirena Huang and 黃凱珉 identify the same person and must resolve to one person record.

## Identity Document (證件)

The required image files of a person's national ID, ARC, or passport, including both sides where applicable. Files are held in private object storage and linked from the person record; the database stores their metadata and verification state, not the image bytes. An engagement cannot become payable until its required identity document is received and internally verified.

## Engagement

One defined piece of work performed by a person, such as a performance, rehearsal, recording session, or stagehand shift. An engagement belongs to a project and may be tied to a specific session.

## Labour Remuneration Receipt (勞報單)

A receipt that documents one engagement and is signed by its payee through DocuSign. The existing 福爾摩沙藝響 receipt template is the authoritative output layout for the initial system. One person who performs four engagements in a month receives and signs four separate receipts.

## Payment Batch

The end-of-month payment run. It groups payable receipts and expense claims by a verified destination bank account so a person can sign multiple receipts but receive one combined transfer. The initial bank export target is Taipei Fubon Bank's TWD bulk transfer/remittance service.

## Payment Account (收款帳戶)

The verified bank destination for a person. Every account identifier—including bank code, branch code, post-office bureau number, and account number—is stored as a string. Leading zeroes and the source-system formatting must be preserved. When a post-office bureau number and account number are supplied separately, the system retains both original fields and may derive a combined payment value without replacing either source value. All person-data identifiers and codes (phone, identity number, account, bank/branch code, vehicle plate, and birth data) are strings; only monetary amounts use numeric types.

## Withholding Entity (扣繳單位)

The single legal entity that pays every initial-scope engagement and is responsible for all withholding-tax and NHI supplementary-premium declarations.

## Expense Claim (墊付核銷)

A claim for an out-of-pocket business expense, submitted by a team member with a photo or file of its invoice or receipt. It records the project, expense date, financial-report category, currency, amount, and business purpose. The category must be selected from the organization's current financial-report category list; it is not a free-text or independently maintained list. Submission makes it payable without a separate approval step. It moves through Draft, Ready for Payment, Included in Payment Batch, Paid, and Voided states. It remains distinct from remuneration and its tax treatment, even if both amounts are combined in one transfer.

## Financial Report Sheet (財報表)

The existing Google Sheet used for financial reporting. It is the reporting destination for submitted expense-claim rows and the source of the permitted expense-category list. It is not used to store identity documents, bank accounts, or signed receipts.

## Payment Readiness (付款就緒)

The status reached after work is complete, the required identity document and payment account are verified, the labour remuneration receipt has been signed, and any reimbursable expense has its required proof. Only payment-ready items may enter a payment batch.
