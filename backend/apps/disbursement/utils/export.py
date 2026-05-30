import csv
import io

from . import normalize_mpesa_number


def generate_bank_csv(transactions, bank_name: str) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    if bank_name.upper() == 'EQUITY':
        writer.writerow(['AccountNumber', 'BeneficiaryName', 'Amount', 'Narration'])
        for txn in transactions:
            writer.writerow([
                txn.recipient_identifier,
                txn.recipient_name,
                float(txn.amount),
                f'Cooperative payment ref {txn.batch_id}',
            ])
    elif bank_name.upper() == 'KCB':
        writer.writerow(['AccountNumber', 'BeneficiaryName', 'Amount', 'Narration'])
        for txn in transactions:
            writer.writerow([
                txn.recipient_identifier,
                txn.recipient_name,
                float(txn.amount),
                f'Coop payment {txn.batch_id}',
            ])
    else:
        writer.writerow(['AccountNumber', 'BeneficiaryName', 'Amount', 'Narration'])
        for txn in transactions:
            writer.writerow([
                txn.recipient_identifier,
                txn.recipient_name,
                float(txn.amount),
                f'Payment batch {txn.batch_id}',
            ])

    return output.getvalue()
