import 'package:flutter/material.dart';

import '../../../domain/activity/entities/invoice.dart';
import 'invoice_details.dart';

/// بطاقة فاتورة في تبويب «فواتيري» — غلاف حول `InvoiceDetails` لا أكثر.
class InvoiceCard extends StatelessWidget {
  const InvoiceCard({required this.invoice, super.key});

  final Invoice invoice;

  @override
  Widget build(BuildContext context) => Card(
    margin: const EdgeInsets.symmetric(vertical: 6),
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: InvoiceDetails(invoice: invoice),
    ),
  );
}
