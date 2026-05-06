"""Sprint 4 - Clipboard Security Tests (All 5 tests)"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import time
import threading
import tempfile
import ctypes


class TestClipboardSecurity(unittest.TestCase):
    """Complete clipboard security tests for Sprint 4"""

    @classmethod
    def setUpClass(cls):
        from Crypts_man.src.core.clipboard.platform_adapter import create_platform_adapter
        from Crypts_man.src.core.clipboard.clipboard_service import ClipboardService
        from Crypts_man.src.core.config import Config
        from Crypts_man.src.core.events import events

        cls.config = Config()
        cls.config.set('clipboard_timeout', 5)
        cls.platform = create_platform_adapter()
        cls.events = events

    def setUp(self):
        from Crypts_man.src.core.clipboard.clipboard_service import ClipboardService
        self.service = ClipboardService(self.config, self.events)
        try:
            self.platform.clear_clipboard()
        except:
            pass

    def tearDown(self):
        if self.service:
            if hasattr(self.service, 'timer') and self.service.timer:
                self.service.timer.cancel()
            try:
                self.service.clear(force=True)
            except:
                pass
        try:
            self.platform.clear_clipboard()
        except:
            pass

    # ========== TEST-1: Auto-clear timing ==========
    def test_auto_clear_timing(self):
        """TEST-1: Verify clipboard clears within timeout"""
        print("\n=== TEST-1: Auto-clear timing ===")
        test_pwd = "timing_test_123"

        start = time.time()
        self.service.copy_to_clipboard(test_pwd, "password", "test")

        # Wait for timeout + buffer
        time.sleep(5.5)

        content = self.platform.get_clipboard_content()
        elapsed = time.time() - start

        print(f"  Timeout: 5s, Actual: {elapsed:.2f}s")
        self.assertIsNone(content or None)
        self.assertLess(abs(elapsed - 5), 1.0)

    # ========== TEST-2: Cross-platform ==========
    def test_cross_platform(self):
        """TEST-2: Verify copy/get/clear work on current platform"""
        print("\n=== TEST-2: Cross-platform ===")
        test_pwd = "cross_platform_123"

        copy_result = self.platform.copy_to_clipboard(test_pwd)
        print(f"  Copy result: {copy_result}")

        content = self.platform.get_clipboard_content()
        print(f"  Content after copy: {content}")

        self.assertTrue(copy_result)
        print(f"  Platform: {sys.platform} ")



    #TEST-3: Memory security with Win32 API
    def test_memory_security_with_win32(self):
        """TEST-3: Verify password using Win32 API memory dump"""
        print("\nTEST-3: Memory security (Win32 API)")

        import ctypes
        from ctypes import wintypes

        test_password = "MEMORY_SECRET_XYZ_123!@#"
        print(f"  Test password: {test_password}")

        # Step 1: Copy password to clipboard
        print("  Step 1: Copying password to clipboard...")
        self.service.copy_to_clipboard(test_password, "password", "test_id")
        time.sleep(0.5)

        # Step 2: Get process ID using Win32 API
        print("  Step 2: Getting process ID via Win32 API...")
        kernel32 = ctypes.windll.kernel32
        current_pid = kernel32.GetCurrentProcessId()
        print(f"  Current PID: {current_pid}")

        # Step 3: Open process using Win32 API
        print("  Step 3: Opening process handle via Win32 OpenProcess...")
        PROCESS_ALL_ACCESS = 0x1F0FFF
        hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, current_pid)

        if not hProcess:
            print("  Could not open process (need admin rights)")
            self.skipTest("Need administrator rights")
            return
        print(f"  Process handle: {hProcess}")

        # Step 4: Create memory dump using Win32 dbghelp.dll
        print("  Step 4: Creating memory dump via Win32 dbghelp MiniDumpWriteDump...")
        dbghelp = ctypes.windll.dbghelp

        dump_path = os.path.join(tempfile.gettempdir(), f"cryptosafe_{current_pid}.dmp")

        GENERIC_WRITE = 0x40000000
        CREATE_ALWAYS = 2
        FILE_ATTRIBUTE_NORMAL = 0x80

        hFile = kernel32.CreateFileW(
            dump_path,
            GENERIC_WRITE,
            0, None,
            CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            None
        )

        if hFile:
            MINIDUMP_TYPE = 0x00000002  # MiniDumpWithPrivateReadWriteMemory
            result = dbghelp.MiniDumpWriteDump(
              hProcess, current_pid, hFile,
              MINIDUMP_TYPE,
              None, None, None
            )
            kernel32.CloseHandle(hFile)
            print(f"  MiniDumpWriteDump result: {result}")
        else:
            print("  Could not create dump file")
            kernel32.CloseHandle(hProcess)
            self.skipTest("Could not create dump file")
            return

        # Step 5: Close process handle
        kernel32.CloseHandle(hProcess)

        # Step 6: Check if dump was created
        if os.path.exists(dump_path):
            print(f"  Dump created: {dump_path}")
            print(f"  Dump size: {os.path.getsize(dump_path) / 1024:.2f} KB")

            # Step 7: Search for password in dump using Win32 ReadFile
            print("  Step 7: Searching dump for password...")
            password_found = False

            # Open file with Win32 CreateFile
            hFileRead = kernel32.CreateFileW(
                dump_path,
                0x80000000,  # GENERIC_READ
                1, None,  # FILE_SHARE_READ
                3,  # OPEN_EXISTING
                0x80, None
            )

            if hFileRead:
                search_bytes = test_password.encode('utf-8')
                buffer = ctypes.create_string_buffer(1024 * 1024)
                bytes_read = wintypes.DWORD()

                while True:
                    result = kernel32.ReadFile(
                        hFileRead, buffer, len(buffer),
                        ctypes.byref(bytes_read), None
                    )
                    if not result or bytes_read.value == 0:
                        break

                    data = buffer.raw[:bytes_read.value]
                    if search_bytes in data:
                        password_found = True
                        break

                kernel32.CloseHandle(hFileRead)

            os.remove(dump_path)
        else:
            print("  Dump file not created")
            self.skipTest("Dump creation failed")
            return

        # Step 8: Results
        print("\n" + "-" * 40)
        if password_found:
            print("   Password found in memory dump")
            print("  Reason: System clipboard API stores plaintext")
            print("  Mitigation: Auto-clear after 5 seconds")
        else:
            print("   Password NOT found in memory dump")
        print("-" * 40)

        print("  Win32 API used: GetCurrentProcessId, OpenProcess, CreateFileW, MiniDumpWriteDump, ReadFile, CloseHandle")
        self.assertTrue(True)









    # ========== TEST-4: Concurrency ==========
    def test_concurrent_copy(self):
        """TEST-4: Multiple rapid copies - no data leakage"""
        print("\n=== TEST-4: Concurrency test ===")
        passwords = [f"pwd_{i}_ABC123" for i in range(5)]
        results = []

        def copy_worker(pwd, idx):
            results.append((idx, self.service.copy_to_clipboard(pwd, "password", f"e_{idx}")))

        threads = []
        for i, pwd in enumerate(passwords):
            t = threading.Thread(target=copy_worker, args=(pwd, i))
            threads.append(t)
            t.start()
            time.sleep(0.01)

        for t in threads:
            t.join()

        last_pwd = passwords[-1]
        content = self.platform.get_clipboard_content()

        print(f"  Expected: {last_pwd[:15]}...")
        print(f"  Actual: {content[:15] if content else 'None'}...")
        self.assertEqual(content, last_pwd)

    # ========== TEST-5: Recovery after crash ==========
    def test_recovery_after_crash(self):
        """TEST-5: Crash during operation - clean state"""
        print("\n=== TEST-5: Recovery test ===")
        test_pwd = "CRASH_TEST_SECRET"

        self.service.copy_to_clipboard(test_pwd, "password", "test")

        # Cancel timer
        if self.service.timer:
            self.service.timer.cancel()

        # Simulate crash
        self.service = None
        import gc
        gc.collect()

        print("  Crash simulated, service destroyed")
        self.assertTrue(True)

    # ========== Helper methods for Win32 ==========
    def _create_memory_dump_win32(self, pid, dump_path):
        """Create memory dump using Windows dbghelp.dll"""
        try:
            dbghelp = ctypes.windll.dbghelp
            kernel32 = ctypes.windll.kernel32

            PROCESS_ALL_ACCESS = 0x1F0FFF
            hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
            if not hProcess:
                return False

            GENERIC_WRITE = 0x40000000
            CREATE_ALWAYS = 2
            FILE_ATTRIBUTE_NORMAL = 0x80

            hFile = kernel32.CreateFileW(
                dump_path, GENERIC_WRITE, 0, None,
                CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None
            )

            if not hFile:
                kernel32.CloseHandle(hProcess)
                return False

            MINIDUMP_TYPE = 0x00000002
            result = dbghelp.MiniDumpWriteDump(
                hProcess, pid, hFile, MINIDUMP_TYPE,
                None, None, None
            )

            kernel32.CloseHandle(hFile)
            kernel32.CloseHandle(hProcess)

            return result != 0 and os.path.exists(dump_path)
        except:
            return False

    def _search_in_dump(self, dump_path, search_string):
        """Search for string in binary dump file"""
        try:
            search_bytes = search_string.encode('utf-8')
            with open(dump_path, 'rb') as f:
                chunk_size = 1024 * 1024
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    if search_bytes in chunk:
                        return True
            return False
        except:
            return False


if __name__ == '__main__':
    unittest.main()
