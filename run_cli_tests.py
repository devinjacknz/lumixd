import os
import sys
import asyncio
import subprocess
import signal
from typing import List, Tuple, Optional
from datetime import datetime

class TestRunner:
    def __init__(self):
        self.env = os.environ.copy()
        self.env['PYTHONPATH'] = '/home/ubuntu/repos/lumixd'
        self.env['WALLET_KEY'] = os.getenv('walletkey_2', '')
        self.env['DEEPSEEK_KEY'] = 'sk-4ff47d34c52948edab6c9d0e7745b75b'
        self.process: Optional[subprocess.Popen] = None
        
    async def _read_until_prompt(self, timeout: float = 30.0) -> List[str]:
        """Read output until prompt or timeout"""
        output = []
        start_time = datetime.now()
        
        while True:
            if (datetime.now() - start_time).total_seconds() > timeout:
                raise TimeoutError("Timeout waiting for prompt")
                
            if not self.process or not self.process.stdout:
                raise RuntimeError("Process not running")
                
            line = self.process.stdout.readline()
            if not line:
                break
                
            line = line.strip()
            output.append(line)
            if '>>>' in line:
                break
                
        return output
        
    async def _write_input(self, text: str) -> None:
        """Write input to process"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not running")
            
        self.process.stdin.write(f"{text}\n")
        self.process.stdin.flush()
        
    async def run_test_case(self, instruction: str, confirm: str = 'y') -> Tuple[int, List[str]]:
        """Run a single test case with the CLI"""
        try:
            # Start the CLI process
            self.process = subprocess.Popen(
                ['python', 'cli_trade.py'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env
            )
            
            # Wait for welcome message
            output = await self._read_until_prompt()
            
            # Send instruction
            await self._write_input(instruction)
            
            # Wait for confirmation prompt
            output.extend(await self._read_until_prompt())
            
            # Send confirmation
            await self._write_input(confirm)
            
            # Get remaining output
            try:
                if self.process and self.process.stdout:
                    while True:
                        line = self.process.stdout.readline()
                        if not line:
                            break
                        output.append(line.strip())
            except Exception as e:
                print(f"Error reading output: {str(e)}")
                pass
                
            return_code = self.process.poll() or 0
            return return_code, output
            
        except Exception as e:
            print(f"Error running test case: {str(e)}")
            return 1, [f"Error: {str(e)}"]
            
        finally:
            if self.process:
                try:
                    if self.process.stdin:
                        self.process.stdin.close()
                except Exception as e:
                    print(f"Error closing stdin: {str(e)}")
                    pass
                    
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    try:
                        self.process.kill()
                    except:
                        pass
                        
                self.process = None
                
    async def run_all_tests(self):
        """Run all test cases"""
        test_cases = [
            ("买入500个SOL代币，滑点不超过2%", "Chinese buy instruction"),
            ("Buy 500 SOL tokens with max 2% slippage", "English buy instruction"),
            ("invalid instruction", "Error case"),
            ("卖出1000000个SOL代币", "Insufficient funds"),
        ]
        
        results = []
        for instruction, description in test_cases:
            print(f"\n=== Running test: {description} ===")
            return_code, output = await self.run_test_case(instruction)
            results.append({
                'description': description,
                'instruction': instruction,
                'return_code': return_code,
                'output': output,
                'passed': return_code == 0 and any('交易分析' in line for line in output)
            })
            
        # Print summary
        print("\n=== Test Summary ===")
        for result in results:
            status = "✅ Passed" if result['passed'] else "❌ Failed"
            print(f"{status} - {result['description']}")
            
        return all(r['passed'] for r in results)
        
async def main():
    """Run all tests"""
    runner = TestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)
    
if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(1))
    asyncio.run(main())
