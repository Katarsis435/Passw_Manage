# Crypts_man/src/core/audit/log_formatters.py
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import logging

logger = logging.getLogger(__name__)


class LogFormatter:
  """Export formatters for audit logs"""

  @staticmethod
  def format_json(entries: List[Dict[str, Any]], include_signatures: bool = True) -> str:
    """
    Format entries as JSON with optional signatures

    Args:
        entries: List of audit entries
        include_signatures: Include cryptographic signatures

    Returns:
        JSON string
    """
    export_data = {
      'export_timestamp': datetime.now().isoformat(),
      'export_version': '1.0',
      'entry_count': len(entries),
      'entries': []
    }

    for entry in entries:
      export_entry = {
        'sequence_number': entry.get('sequence_number'),
        'timestamp': entry.get('timestamp'),
        'event_type': entry.get('event_type'),
        'severity': entry.get('severity'),
        'user_id': entry.get('user_id'),
        'source': entry.get('source'),
        'details': entry.get('entry_data', {}) if isinstance(entry.get('entry_data'), dict) else json.loads(
          entry.get('entry_data', '{}')),
        'entry_hash': entry.get('entry_hash')
      }

      if include_signatures:
        export_entry['signature'] = entry.get('signature')

      export_data['entries'].append(export_entry)

    return json.dumps(export_data, indent=2, default=str)

  @staticmethod
  def format_csv(entries: List[Dict[str, Any]]) -> str:
    """
    Format entries as CSV for spreadsheet analysis

    Args:
        entries: List of audit entries

    Returns:
        CSV string
    """
    output = io.StringIO()

    # Define columns
    fieldnames = ['sequence_number', 'timestamp', 'event_type', 'severity', 'user_id', 'source', 'details_summary']

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for entry in entries:
      # Get details as string summary
      details = entry.get('entry_data', {})
      if isinstance(details, str):
        try:
          details = json.loads(details)
        except:
          details = {'raw': details[:100]}

      details_summary = json.dumps(details, ensure_ascii=False)[:200]

      writer.writerow({
        'sequence_number': entry.get('sequence_number'),
        'timestamp': entry.get('timestamp'),
        'event_type': entry.get('event_type'),
        'severity': entry.get('severity'),
        'user_id': entry.get('user_id'),
        'source': entry.get('source'),
        'details_summary': details_summary
      })

    return output.getvalue()

  @staticmethod
  def format_pdf(entries: List[Dict[str, Any]], title: str = "Audit Log Report") -> bytes:
    """
    Format entries as PDF report

    Args:
        entries: List of audit entries
        title: Report title

    Returns:
        PDF bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()

    # Custom style for title
    title_style = ParagraphStyle(
      'CustomTitle',
      parent=styles['Heading1'],
      fontSize=16,
      spaceAfter=30
    )

    story = []

    # Title
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"Generated: {datetime.now().isoformat()}", styles['Normal']))
    story.append(Paragraph(f"Total Entries: {len(entries)}", styles['Normal']))
    story.append(Spacer(1, 0.2 * inch))

    # Summary statistics
    summary = LogFormatter._get_summary_stats(entries)
    summary_data = [
      ['Statistic', 'Value'],
      ['Total Events', str(summary['total'])],
      ['CRITICAL Events', str(summary['critical'])],
      ['ERROR Events', str(summary['error'])],
      ['WARNING Events', str(summary['warning'])],
      ['INFO Events', str(summary['info'])],
      ['Unique Users', str(summary['unique_users'])]
    ]

    summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
    summary_table.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
      ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
      ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, 0), 12),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
      ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
      ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    # Entries table
    entry_data = [['Seq', 'Time', 'Event', 'Severity', 'User', 'Details']]

    for entry in entries[:100]:  # Limit to 100 entries for PDF
      details = entry.get('entry_data', {})
      if isinstance(details, str):
        try:
          details = json.loads(details)
        except:
          details = {'message': details[:50]}

      details_str = json.dumps(details, ensure_ascii=False)[:80]

      entry_data.append([
        str(entry.get('sequence_number', '')),
        entry.get('timestamp', '')[:19],
        entry.get('event_type', '')[:30],
        entry.get('severity', ''),
        entry.get('user_id', '')[:15],
        details_str
      ])

    # Create table with automatic sizing
    entry_table = Table(entry_data, repeatRows=1)
    entry_table.setStyle(TableStyle([
      ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
      ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
      ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
      ('FONTSIZE', (0, 0), (-1, 0), 10),
      ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
      ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
      ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))

    story.append(entry_table)

    # Build PDF
    doc.build(story)
    return buffer.getvalue()

  @staticmethod
  def _get_summary_stats(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics for report"""
    stats = {
      'total': len(entries),
      'critical': 0,
      'error': 0,
      'warning': 0,
      'info': 0,
      'unique_users': set()
    }

    for entry in entries:
      severity = entry.get('severity', '')
      if severity == 'CRITICAL':
        stats['critical'] += 1
      elif severity == 'ERROR':
        stats['error'] += 1
      elif severity == 'WARN':
        stats['warning'] += 1
      else:
        stats['info'] += 1

      user_id = entry.get('user_id')
      if user_id:
        stats['unique_users'].add(user_id)

    stats['unique_users'] = len(stats['unique_users'])
    return stats

  @staticmethod
  def format_signed_export(entries: List[Dict[str, Any]], public_key: str, algorithm: str) -> str:
    """
    Format entries as signed JSON for external verification

    Args:
        entries: List of audit entries
        public_key: Public key hex string
        algorithm: Signing algorithm used

    Returns:
        Signed JSON string
    """
    export_data = {
      'export_timestamp': datetime.now().isoformat(),
      'export_version': '1.0',
      'verification_info': {
        'public_key': public_key,
        'algorithm': algorithm,
        'verification_instructions': 'Use the public key above to verify signatures'
      },
      'entries': []
    }

    for entry in entries:
      export_data['entries'].append({
        'sequence_number': entry.get('sequence_number'),
        'timestamp': entry.get('timestamp'),
        'event_type': entry.get('event_type'),
        'severity': entry.get('severity'),
        'user_id': entry.get('user_id'),
        'source': entry.get('source'),
        'details': json.loads(entry.get('entry_data', '{}')) if isinstance(entry.get('entry_data'), str) else entry.get(
          'entry_data', {}),
        'entry_hash': entry.get('entry_hash'),
        'signature': entry.get('signature')
      })

    return json.dumps(export_data, indent=2, default=str)
