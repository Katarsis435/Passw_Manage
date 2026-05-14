# Crypts_man/src/core/audit/log_verifier.py
import json
import hashlib
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
  """Result of log integrity verification"""
  verified: bool = True
  total_entries: int = 0
  valid_entries: int = 0
  invalid_signatures: List[Dict] = field(default_factory=list)
  chain_breaks: List[Dict] = field(default_factory=list)
  hash_mismatches: List[Dict] = field(default_factory=list)
  tampered_entries: List[int] = field(default_factory=list)
  verification_time: float = 0.0

  def to_dict(self) -> Dict:
    return {
      'verified': self.verified,
      'total_entries': self.total_entries,
      'valid_entries': self.valid_entries,
      'invalid_signatures': self.invalid_signatures,
      'chain_breaks': self.chain_breaks,
      'hash_mismatches': self.hash_mismatches,
      'tampered_entries': self.tampered_entries,
      'verification_time': self.verification_time
    }

  def to_report(self) -> str:
    """Generate human-readable report"""
    lines = [
      "=" * 50,
      "AUDIT LOG INTEGRITY VERIFICATION REPORT",
      "=" * 50,
      f"Verification Time: {datetime.now().isoformat()}",
      f"Total Entries: {self.total_entries}",
      f"Valid Entries: {self.valid_entries}",
      f"Tampered Entries: {len(self.tampered_entries)}",
      f"Chain Breaks: {len(self.chain_breaks)}",
      f"Hash Mismatches: {len(self.hash_mismatches)}",
      f"Overall Status: {'✅ VERIFIED' if self.verified else '❌ TAMPERED'}",
      "-" * 50,
    ]

    if self.invalid_signatures:
      lines.append("\nINVALID SIGNATURES:")
      for inv in self.invalid_signatures[:10]:
        lines.append(f"  • Sequence {inv.get('sequence')}: {inv.get('reason')}")

    if self.chain_breaks:
      lines.append("\nCHAIN BREAKS:")
      for break_info in self.chain_breaks[:10]:
        lines.append(
          f"  • Sequence {break_info.get('sequence')}: expected {break_info.get('expected')[:16]}..., got {break_info.get('actual')[:16]}...")

    if self.hash_mismatches:
      lines.append("\nHASH MISMATCHES:")
      for mismatch in self.hash_mismatches[:10]:
        lines.append(f"  • Sequence {mismatch.get('sequence')}: {mismatch.get('reason')}")

    return "\n".join(lines)


class LogVerifier:
  """Log integrity verification service"""

  def __init__(self, db_connection, signer):
    """
    Initialize verifier

    Args:
        db_connection: Database connection
        signer: AuditLogSigner instance for signature verification
    """
    self.db = db_connection
    self.signer = signer

  def verify_full(self) -> VerificationResult:
    """Verify complete log integrity"""
    result = VerificationResult()
    start_time = datetime.now()

    try:
      with self.db.cursor() as c:
        c.execute("""
                    SELECT sequence_number, entry_data, signature, entry_hash, previous_hash
                    FROM audit_log
                    ORDER BY sequence_number
                """)
        rows = c.fetchall()

      result.total_entries = len(rows)
      previous_hash = None

      for row in rows:
        if isinstance(row, sqlite3.Row):
          seq = row['sequence_number']
          entry_data = row['entry_data']
          signature_hex = row['signature']
          stored_hash = row['entry_hash']
          prev_hash = row['previous_hash']
        else:
          seq, entry_data, signature_hex, stored_hash, prev_hash = row

        # Parse entry data
        try:
          entry_json = entry_data if isinstance(entry_data, str) else entry_data.decode()
          entry_dict = json.loads(entry_json)
        except Exception as e:
          result.invalid_signatures.append({
            'sequence': seq,
            'reason': f'Invalid JSON: {e}'
          })
          result.verified = False
          result.tampered_entries.append(seq)
          continue

        # Verify signature
        signature = bytes.fromhex(signature_hex)
        data_bytes = entry_data.encode() if isinstance(entry_data, str) else entry_data

        if not self.signer.verify(data_bytes, signature):
          result.invalid_signatures.append({
            'sequence': seq,
            'reason': 'Invalid signature'
          })
          result.verified = False
          result.tampered_entries.append(seq)
          continue

        # Verify hash chain
        if previous_hash is not None and prev_hash != previous_hash:
          result.chain_breaks.append({
            'sequence': seq,
            'expected': previous_hash,
            'actual': prev_hash
          })
          result.verified = False
          result.tampered_entries.append(seq)

        # Verify entry hash
        computed_hash = hashlib.sha256(data_bytes).hexdigest()
        if computed_hash != stored_hash:
          result.hash_mismatches.append({
            'sequence': seq,
            'reason': f'Hash mismatch: expected {stored_hash[:16]}..., got {computed_hash[:16]}...'
          })
          result.verified = False
          result.tampered_entries.append(seq)
          continue

        result.valid_entries += 1
        previous_hash = stored_hash

    except Exception as e:
      logger.error(f"Verification failed: {e}")
      result.verified = False

    result.verification_time = (datetime.now() - start_time).total_seconds()

    # Store verification result
    self._store_verification_result(result)

    # Trigger security event if tampering detected
    if not result.verified:
      self._handle_tampering(result)

    return result

  def verify_range(self, start_seq: int, end_seq: Optional[int] = None) -> VerificationResult:
    """Verify a range of log entries"""
    result = VerificationResult()

    with self.db.cursor() as c:
      if end_seq:
        c.execute("""
                    SELECT sequence_number, entry_data, signature, entry_hash, previous_hash
                    FROM audit_log
                    WHERE sequence_number BETWEEN ? AND ?
                    ORDER BY sequence_number
                """, (start_seq, end_seq))
      else:
        c.execute("""
                    SELECT sequence_number, entry_data, signature, entry_hash, previous_hash
                    FROM audit_log
                    WHERE sequence_number >= ?
                    ORDER BY sequence_number
                """, (start_seq,))
      rows = c.fetchall()

    result.total_entries = len(rows)
    previous_hash = None

    for row in rows:
      if isinstance(row, sqlite3.Row):
        seq = row['sequence_number']
        entry_data = row['entry_data']
        signature_hex = row['signature']
        stored_hash = row['entry_hash']
        prev_hash = row['previous_hash']
      else:
        seq, entry_data, signature_hex, stored_hash, prev_hash = row

      # Verify signature
      signature = bytes.fromhex(signature_hex)
      data_bytes = entry_data.encode() if isinstance(entry_data, str) else entry_data

      if not self.signer.verify(data_bytes, signature):
        result.invalid_signatures.append({
          'sequence': seq,
          'reason': 'Invalid signature'
        })
        result.verified = False
        continue

      # Verify hash chain
      if previous_hash is not None and prev_hash != previous_hash:
        result.chain_breaks.append({
          'sequence': seq,
          'expected': previous_hash,
          'actual': prev_hash
        })
        result.verified = False

      # Verify entry hash
      computed_hash = hashlib.sha256(data_bytes).hexdigest()
      if computed_hash != stored_hash:
        result.hash_mismatches.append({
          'sequence': seq,
          'reason': 'Hash mismatch'
        })
        result.verified = False
        continue

      result.valid_entries += 1
      previous_hash = stored_hash

    return result

  def verify_recent(self, count: int = 1000) -> VerificationResult:
    """Verify most recent N entries"""
    with self.db.cursor() as c:
      c.execute("SELECT MAX(sequence_number) FROM audit_log")
      max_seq = c.fetchone()[0]

    if max_seq is None:
      return VerificationResult()

    start_seq = max(0, max_seq - count + 1)
    return self.verify_range(start_seq)

  def _store_verification_result(self, result: VerificationResult):
    """Store verification result in database"""
    with self.db.cursor() as c:
      c.execute("""
                INSERT INTO audit_integrity_checks
                (total_entries, valid_entries, tampered_entries, hash_chain_breaks, check_result, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
        result.total_entries,
        result.valid_entries,
        len(result.tampered_entries),
        len(result.chain_breaks),
        'PASS' if result.verified else 'FAIL',
        json.dumps(result.to_dict())
      ))

  def _handle_tampering(self, result: VerificationResult):
    """Handle tampering detection"""
    logger.critical(f"Tampering detected in audit log! {len(result.tampered_entries)} entries affected")

    # This would trigger security events
    # In a future sprint, this would lock the vault and require re-authentication
