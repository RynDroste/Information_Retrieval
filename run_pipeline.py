#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import subprocess
import time
import json
import shutil
import signal
import platform
from pathlib import Path

try:
    import urllib.request
    import urllib.parse
except ImportError:
    print("Error: urllib is required but not available")
    sys.exit(1)

from scraper import RamenScraper
from data_cleaner import DataCleaner
from solr_indexer import SolrIndexer


class SolrConfigurator:
    
    def __init__(self, solr_url='http://localhost:8983/solr/RamenProject'):
        self.solr_url = solr_url
        self.core_name = solr_url.split('/')[-1]
        self.script_dir = Path(__file__).parent
        
    def check_solr_connection(self):
        try:
            ping_url = f"{self.solr_url}/admin/ping"
            req = urllib.request.Request(ping_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.getcode() == 200
        except Exception as e:
            print(f"Failed to connect to Solr: {e}")
            return False
    
    def copy_synonyms_file(self):
        synonyms_file = self.script_dir / 'solr_config' / 'synonyms.txt'
        stopwords_file = self.script_dir / 'solr_config' / 'stopwords.txt'
        
        possible_dirs = [
            Path(f"/opt/homebrew/var/lib/solr/{self.core_name}/conf"),
            Path(f"/usr/local/var/lib/solr/{self.core_name}/conf"),
            Path(f"/var/solr/data/{self.core_name}/conf"),
        ]
        
        copied = False
        for conf_dir in possible_dirs:
            if conf_dir.exists():
                try:
                    if synonyms_file.exists():
                        shutil.copy2(synonyms_file, conf_dir / 'synonyms.txt')
                        print(f"Copied synonyms.txt to {conf_dir}")
                    if stopwords_file.exists():
                        shutil.copy2(stopwords_file, conf_dir / 'stopwords.txt')
                        print(f"Copied stopwords.txt to {conf_dir}")
                    copied = True
                    break
                except Exception as e:
                    print(f"Failed to copy files to {conf_dir}: {e}")
        
        if not copied:
            print("Warning: Solr conf directory not found, please manually copy synonyms.txt and stopwords.txt")
            print(f"   Copy from {self.script_dir / 'solr_config'} to Solr core conf directory")
        
        return copied
    
    def configure_field_type(self):
        field_type_config = {
            "replace-field-type": {
                "name": "text_synonym",
                "class": "solr.TextField",
                "positionIncrementGap": "100",
                "analyzer": {
                    "tokenizer": {"class": "solr.StandardTokenizerFactory"},
                    "filters": [
                        {"class": "solr.LowerCaseFilterFactory"},
                        {"class": "solr.EnglishPossessiveFilterFactory"},
                        {"class": "solr.PorterStemFilterFactory"},
                        {"class": "solr.SynonymGraphFilterFactory", 
                         "synonyms": "synonyms.txt", 
                         "ignoreCase": True, 
                         "expand": True},
                        {"class": "solr.FlattenGraphFilterFactory"},
                        {"class": "solr.EdgeNGramFilterFactory", 
                         "minGramSize": "2", 
                         "maxGramSize": "50"},
                        {"class": "solr.StopFilterFactory", 
                         "words": "stopwords.txt", 
                         "ignoreCase": True}
                    ]
                },
                "queryAnalyzer": {
                    "tokenizer": {"class": "solr.StandardTokenizerFactory"},
                    "filters": [
                        {"class": "solr.LowerCaseFilterFactory"},
                        {"class": "solr.EnglishPossessiveFilterFactory"},
                        {"class": "solr.PorterStemFilterFactory"},
                        {"class": "solr.SynonymGraphFilterFactory", 
                         "synonyms": "synonyms.txt", 
                         "ignoreCase": True, 
                         "expand": True},
                        {"class": "solr.EdgeNGramFilterFactory", 
                         "minGramSize": "2", 
                         "maxGramSize": "50"},
                        {"class": "solr.StopFilterFactory", 
                         "words": "stopwords.txt", 
                         "ignoreCase": True}
                    ]
                }
            }
        }
        
        url = f"{self.solr_url}/schema/fieldtypes/text_synonym"
        data = json.dumps(field_type_config).encode('utf-8')
        
        try:
            req = urllib.request.Request(url, data=data, 
                                       headers={'Content-Type': 'application/json'})
            req.get_method = lambda: 'POST'
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('responseHeader', {}).get('status') == 0:
                    print("Field type configured successfully")
                    return True
                else:
                    print("Field type may not exist, trying to add...")
                    return self._add_field_type(field_type_config)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return self._add_field_type(field_type_config)
            else:
                print(f"Failed to configure field type: {e.code} {e.reason}")
                return False
        except Exception as e:
            print(f"Error configuring field type: {e}")
            return False
    
    def _add_field_type(self, field_type_config):
        url = f"{self.solr_url}/schema/fieldtypes"
        field_type_def = field_type_config.get("replace-field-type", {})
        add_config = {"add-field-type": field_type_def}
        data = json.dumps(add_config).encode('utf-8')
        
        try:
            req = urllib.request.Request(url, data=data,
                                       headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('responseHeader', {}).get('status') == 0:
                    print("Field type added successfully")
                    return True
                else:
                    print(f"Field type may already exist: {result}")
                    return True
        except Exception as e:
            print(f"Failed to add field type: {e}")
            return False
    
    def add_field_if_not_exists(self, field_name, field_type='string', indexed=True, stored=True):
        """Add a field to Solr schema if it doesn't exist"""
        url = f"{self.solr_url}/schema/fields"
        field_config = {
            "add-field": {
                "name": field_name,
                "type": field_type,
                "indexed": indexed,
                "stored": stored
            }
        }
        data = json.dumps(field_config).encode('utf-8')
        
        try:
            req = urllib.request.Request(url, data=data,
                                       headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('responseHeader', {}).get('status') == 0:
                    print(f"{field_name} field added successfully")
                    return True
                else:
                    error_msg = result.get('error', {}).get('msg', '')
                    if 'already exists' in error_msg or 'duplicate' in error_msg.lower():
                        print(f"{field_name} field already exists")
                        return True
                    print(f"{field_name} field may already exist: {result}")
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 400:
                error_body = e.read().decode('utf-8')
                if 'already exists' in error_body or 'duplicate' in error_body.lower():
                    print(f"{field_name} field already exists")
                    return True
            print(f"{field_name} field add failed: {e}")
            return False
        except Exception as e:
            print(f"{field_name} field add failed: {e}")
            return False
    
    def update_fields(self):
        fields = ["title", "content", "menu_item", "introduction"]
        success_count = 0
        
        for field in fields:
            url = f"{self.solr_url}/schema/fields/{field}"
            field_config = {
                "replace-field": {
                    "name": field,
                    "type": "text_synonym",
                    "indexed": True,
                    "stored": True
                }
            }
            data = json.dumps(field_config).encode('utf-8')
            
            try:
                req = urllib.request.Request(url, data=data,
                                           headers={'Content-Type': 'application/json'})
                req.get_method = lambda: 'POST'
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    if result.get('responseHeader', {}).get('status') == 0:
                        print(f"{field} field updated successfully")
                        success_count += 1
                    else:
                        print(f"{field} field update may have failed: {result}")
            except Exception as e:
                print(f"{field} field update failed: {e}")
        
        # Add price field if it doesn't exist
        self.add_field_if_not_exists('price', field_type='string', indexed=True, stored=True)
        
        # Add price_range field if it doesn't exist
        self.add_field_if_not_exists('price_range', field_type='string', indexed=True, stored=True)
        
        return success_count > 0
    
    def configure(self):
        print("\nConfiguring Solr core...")
        
        if not self.check_solr_connection():
            print("Cannot connect to Solr, skipping configuration")
            return False
        
        print("Connected to Solr")
        
        self.copy_synonyms_file()
        
        if not self.configure_field_type():
            print("Field type configuration failed")
            return False
        
        if not self.update_fields():
            print("Some field updates failed, but configuration may still be usable")
        
        print("Solr configuration completed")
        return True


class PipelineRunner:
    def __init__(self, skip_scrape=False, skip_clean=False, skip_index=False, 
                 start_frontend=False, configure_solr=False,
                 solr_url='http://localhost:8983/solr/RamenProject', use_labse=False):
        self.skip_scrape = skip_scrape
        self.skip_clean = skip_clean
        self.skip_index = skip_index
        self.start_frontend = start_frontend
        self.configure_solr = configure_solr
        self.solr_url = solr_url
        self.use_labse = use_labse
        self.errors = []
        
    def print_header(self, step_name):
        print("\n" + "=" * 80)
        print(f"📋 {step_name}")
        print("=" * 80)
    
    def step1_scrape(self):
        if self.skip_scrape:
            print("\n⏭️  Skipping scrape step")
            return True
            
        self.print_header("Step 1/3: Scraping website data")
        
        try:
            scraper = RamenScraper()
            
            # Scraping from https://afuri.com - only store and brand information
            scraper.scrape_store_information()
            scraper.scrape_brand_info()
            
            # Also scraping from shop.afuri.com
            scraper.scrape_shop_products()
            
            # Scraping from https://ec-ippudo.com/shop/default.aspx
            scraper.scrape_ippudo_products()
            
            filepath = scraper.save_data()
            
            if filepath and os.path.exists(filepath):
                print(f"\n✓ Scraping completed! Data saved to: {filepath}")
                return True
            else:
                print("\n✗ Scraping failed: data file not generated")
                return False
                
        except Exception as e:
            error_msg = f"Error during scraping: {str(e)}"
            print(f"\n✗ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def step2_clean(self):
        if self.skip_clean:
            print("\n⏭️  Skipping clean step")
            return True
            
        self.print_header("Step 2/3: Cleaning data")
        
        input_file = 'data/scraped_data.json'
        if not os.path.exists(input_file):
            print(f"\n✗ Error: Input file not found {input_file}")
            print("Please run scraping step first")
            return False
        
        try:
            cleaner = DataCleaner()
            
            if cleaner.clean_all():
                cleaner.save_data()
                cleaner.print_stats()
                print(f"\n✓ Cleaning completed! Data saved to: {cleaner.output_file}")
                return True
            else:
                print("\n✗ Cleaning failed")
                return False
                
        except Exception as e:
            error_msg = f"Error during cleaning: {str(e)}"
            print(f"\n✗ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def step0_configure_solr(self):
        if not self.configure_solr:
            return True
        
        self.print_header("Step 0: Configuring Solr")
        
        try:
            configurator = SolrConfigurator(solr_url=self.solr_url)
            if configurator.configure():
                print("\n✓ Solr configuration completed!")
                return True
            else:
                print("\n✗ Solr configuration failed")
                self.errors.append("Solr configuration failed")
                return False
        except Exception as e:
            error_msg = f"Error during Solr configuration: {str(e)}"
            print(f"\n✗ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def step3_index(self):
        if self.skip_index:
            print("\n⏭️  Skipping index step")
            return True
            
        self.print_header("Step 3/3: Indexing to Solr")
        
        input_file = 'data/cleaned_data.json'
        if not os.path.exists(input_file):
            print(f"\n✗ Error: Input file not found {input_file}")
            print("Please run cleaning step first")
            return False
        
        try:
            indexer = SolrIndexer(solr_url=self.solr_url, use_labse=self.use_labse)
            
            if indexer.index_articles(clear_existing=True):
                indexer.print_stats()
                print("\n✓ Indexing completed!")
                return True
            else:
                print("\n✗ Indexing failed")
                return False
                
        except Exception as e:
            error_msg = f"Error during indexing: {str(e)}"
            print(f"\n✗ {error_msg}")
            self.errors.append(error_msg)
            return False
    
    def stop_existing_semantic_api(self):
        """Stop existing semantic search API process if running"""
        try:
            if platform.system() == 'Windows':
                # Windows: use tasklist (simplified - may not work perfectly)
                return
            else:
                # Unix-like: try pgrep first (more reliable)
                try:
                    result = subprocess.run(
                        ['pgrep', '-f', 'semantic_api.py'],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        pids = result.stdout.strip().split('\n')
                        for pid_str in pids:
                            if pid_str:
                                try:
                                    pid = int(pid_str)
                                    print(f"Found existing semantic API process (PID: {pid}), stopping...")
                                    self._kill_process(pid)
                                    print("✓ Stopped existing semantic API")
                                except (ValueError, ProcessLookupError):
                                    continue
                        return
                except FileNotFoundError:
                    # pgrep not available, fall back to ps
                    pass
                
                # Fallback: use ps aux
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'semantic_api.py' in line and 'grep' not in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[1])
                                    print(f"Found existing semantic API process (PID: {pid}), stopping...")
                                    self._kill_process(pid)
                                    print("✓ Stopped existing semantic API")
                                    break
                                except (ValueError, IndexError, ProcessLookupError):
                                    continue
        except Exception:
            # Silently fail - not critical if we can't stop existing process
            pass
    
    def _kill_process(self, pid):
        """Helper method to kill a process gracefully"""
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            # Check if still running
            try:
                os.kill(pid, 0)  # Check if process exists
                print("Process still running, force killing...")
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Process already stopped
        except ProcessLookupError:
            print("Process already stopped")
        except PermissionError:
            print("⚠ No permission to stop process")
    
    def kill_existing_processes(self):
        """Kill existing processes that might conflict"""
        print("Checking for existing processes...")
        found_any = False
        
        try:
            # Find and kill processes by name
            processes_to_kill = [
                ('solr_proxy.py', '[s]olr_proxy.py'),
                ('semantic_api.py', '[s]emantic_api.py'),
                ('http.server', '[h]ttp.server.*8000'),
            ]
            
            for name, pattern in processes_to_kill:
                try:
                    result = subprocess.run(
                        ['ps', 'aux'], 
                        capture_output=True, 
                        text=True, 
                        timeout=5
                    )
                    if result.returncode == 0:
                        lines = result.stdout.split('\n')
                        pids = []
                        for line in lines:
                            if pattern.replace('[', '').replace(']', '') in line and 'grep' not in line:
                                parts = line.split()
                                if len(parts) > 1:
                                    try:
                                        pids.append(int(parts[1]))
                                    except (ValueError, IndexError):
                                        pass
                        
                        if pids:
                            print(f"  → Found existing {name} processes, killing them...")
                            for pid in pids:
                                try:
                                    os.kill(pid, signal.SIGKILL)
                                    found_any = True
                                except (ProcessLookupError, PermissionError):
                                    pass
                            time.sleep(1)
                except Exception as e:
                    pass
            
            # Check ports using lsof if available
            ports_to_check = [8000, 8888, 8889]
            if shutil.which('lsof'):
                for port in ports_to_check:
                    try:
                        result = subprocess.run(
                            ['lsof', '-ti', str(port)],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            pids = [int(p) for p in result.stdout.strip().split('\n') if p.strip()]
                            if pids:
                                print(f"  → Found processes using port {port}, killing them...")
                                for pid in pids:
                                    try:
                                        os.kill(pid, signal.SIGKILL)
                                        found_any = True
                                    except (ProcessLookupError, PermissionError):
                                        pass
                                time.sleep(1)
                    except Exception:
                        pass
            
            if found_any:
                print("✓ Cleanup complete")
            else:
                print("✓ No existing processes found")
            print()
        except Exception as e:
            print(f"⚠ Warning during cleanup: {e}")
            print()
    
    def check_and_generate_embeddings(self):
        """Check if embeddings file exists and generate if needed"""
        embeddings_file = Path(__file__).parent / 'data' / 'embeddings.json'
        cleaned_data_file = Path(__file__).parent / 'data' / 'cleaned_data.json'
        
        if not embeddings_file.exists():
            print("⚠ Embeddings file not found: data/embeddings.json")
            print("Checking if we can generate embeddings...")
            
            if cleaned_data_file.exists():
                print("✓ Found cleaned_data.json, generating embeddings...")
                print("This may take a few minutes (first time will download LaBSE model ~1.2GB)...")
                
                # Run pipeline to generate embeddings
                subprocess.run([
                    sys.executable, str(Path(__file__)),
                    '--use-labse', '--skip-scrape', '--skip-clean'
                ], cwd=Path(__file__).parent)
                
                if embeddings_file.exists():
                    try:
                        with open(embeddings_file, 'r') as f:
                            data = json.load(f)
                        count = len(data)
                        print(f"✓ Generated embeddings file with {count} embeddings")
                        return True
                    except Exception as e:
                        print(f"⚠ Failed to verify embeddings file: {e}")
                        return False
                else:
                    print("⚠ Failed to generate embeddings file")
                    return False
            else:
                print("⚠ cleaned_data.json not found")
                print("⚠ Please run: python3 run_pipeline.py --use-labse --configure-solr")
                return False
        else:
            # Verify embeddings file is valid
            try:
                with open(embeddings_file, 'r') as f:
                    data = json.load(f)
                count = len(data)
                if count == 0:
                    print("⚠ Embeddings file exists but appears to be empty or invalid")
                    print("⚠ Regenerating embeddings...")
                    if cleaned_data_file.exists():
                        subprocess.run([
                            sys.executable, str(Path(__file__)),
                            '--use-labse', '--skip-scrape', '--skip-clean'
                        ], cwd=Path(__file__).parent)
                        return embeddings_file.exists()
                    else:
                        print("⚠ cleaned_data.json not found, cannot regenerate embeddings")
                        return False
                else:
                    print(f"✓ Found embeddings file with {count} embeddings")
                    return True
            except Exception as e:
                print(f"⚠ Error reading embeddings file: {e}")
                return False
    
    def verify_semantic_api(self, max_retries=6, retry_delay=3):
        """Verify that semantic API is available and loaded embeddings"""
        import urllib.request
        
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request('http://localhost:8889/semantic/status')
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    available = data.get('available', False)
                    count = data.get('embeddings_count', 0)
                    
                    if available and count > 0:
                        print(f"  ✓ Semantic API ready with {count} embeddings")
                        return True
            except Exception:
                pass
            
            if attempt < max_retries - 1:
                print(f"  → Waiting for API to load embeddings... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
        
        return False
    
    def step4_start_services(self):
        if not self.start_frontend:
            return True
        
        # Kill existing processes
        self.kill_existing_processes()
        
        self.print_header("Starting frontend services")
        
        script_dir = Path(__file__).parent
        processes = []
        
        try:
            # Check and generate embeddings if using LaBSE
            if self.use_labse:
                print("Checking semantic search setup...")
                print("  → Will verify/generate embeddings before starting API")
                if not self.check_and_generate_embeddings():
                    print("  ⚠ Semantic search API will start but may not be available")
                print()
            
            print("Starting Solr proxy server on port 8888...")
            if self.use_labse:
                print("Starting semantic search API on port 8889...")
            print("Starting frontend server on port 8000...")
            print()
            print("📱 Open in your browser:")
            print("   http://localhost:8000/frontend/")
            print()
            print("Press Ctrl+C to stop all servers")
            print("=" * 80)
            print()
            
            # Set environment variable to avoid tokenizers warning when forking
            env = os.environ.copy()
            env['TOKENIZERS_PARALLELISM'] = 'false'
            
            # Start Solr proxy
            proxy_process = subprocess.Popen(
                [sys.executable, str(script_dir / 'solr_proxy.py')],
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            processes.append(('Solr Proxy', proxy_process))
            time.sleep(2)
            
            # Start semantic API if using LaBSE
            semantic_process = None
            if self.use_labse:
                semantic_api_file = script_dir / 'semantic_api.py'
                if semantic_api_file.exists():
                    print("Starting semantic search API...")
                    semantic_process = subprocess.Popen(
                        [sys.executable, str(semantic_api_file)],
                        cwd=script_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env
                    )
                    processes.append(('Semantic API', semantic_process))
                    
                    # Wait and verify API
                    print("  → Waiting for API server to start...")
                    time.sleep(2)
                    
                    if semantic_process.poll() is None:  # Process still running
                        if not self.verify_semantic_api():
                            print("  ⚠ Warning: Semantic API started but embeddings not loaded")
                            print("  ⚠ Trying to restart API...")
                            semantic_process.terminate()
                            semantic_process.wait(timeout=5)
                            time.sleep(2)
                            
                            # Restart
                            semantic_process = subprocess.Popen(
                                [sys.executable, str(semantic_api_file)],
                                cwd=script_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=env
                            )
                            processes[-1] = ('Semantic API', semantic_process)
                            time.sleep(4)
                            
                            if not self.verify_semantic_api():
                                print("  ✗ Semantic API still not available after restart")
                                print("  ⚠ Please check the API logs for errors")
                    else:
                        print("  ✗ Semantic API process failed to start")
                else:
                    print("⚠ Warning: semantic_api.py not found, skipping semantic API")
            
            # Setup signal handlers
            def signal_handler(sig, frame):
                print("\n\nStopping servers...")
                for name, proc in processes:
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Start frontend server (blocking)
            print("Frontend server running...")
            frontend_process = subprocess.Popen(
                [sys.executable, '-m', 'http.server', '8000'],
                cwd=script_dir,
                env=env
            )
            processes.append(('Frontend Server', frontend_process))
            
            # Wait for frontend server
            frontend_process.wait()
            
        except KeyboardInterrupt:
            print("\n\nStopping servers...")
            for name, proc in processes:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        except Exception as e:
            error_msg = f"Error starting services: {str(e)}"
            print(f"\n✗ {error_msg}")
            self.errors.append(error_msg)
            # Cleanup on error
            for name, proc in processes:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            return False
        
        return True
    
    def run(self):
        print("\n" + "=" * 80)
        print("🚀 AFURI Data Processing Pipeline")
        print("=" * 80)
        print(f"Working directory: {os.getcwd()}")
        print(f"Solr URL: {self.solr_url}")
        print("=" * 80)
        
        os.makedirs('data', exist_ok=True)
        
        success = True
        
        if self.configure_solr:
            if not self.step0_configure_solr():
                print("\n⚠️  Solr configuration failed, but continuing...")
        
        if not self.step1_scrape():
            success = False
            if not self.skip_scrape:
                print("\n❌ Pipeline failed at scraping step, stopping execution")
                return False
        
        if not self.step2_clean():
            success = False
            if not self.skip_clean:
                print("\n❌ Pipeline failed at cleaning step, stopping execution")
                return False
        
        if not self.step3_index():
            success = False
            if not self.skip_index:
                print("\n❌ Pipeline failed at indexing step, stopping execution")
                return False
        
        if success and self.start_frontend:
            self.step4_start_services()
        
        print("\n" + "=" * 80)
        if success:
            print("✅ Pipeline execution completed!")
            if self.errors:
                print(f"\n⚠️  {len(self.errors)} warning(s):")
                for error in self.errors:
                    print(f"  - {error}")
        else:
            print("❌ Pipeline execution failed")
            if self.errors:
                print("\nError messages:")
                for error in self.errors:
                    print(f"  - {error}")
        print("=" * 80)
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description='AFURI data processing pipeline: scrape -> clean -> index',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_pipeline.py --configure-solr --start-frontend
  python3 run_pipeline.py
  python3 run_pipeline.py --skip-scrape
  python3 run_pipeline.py --skip-scrape --skip-clean
  python3 run_pipeline.py --start-frontend
  python3 run_pipeline.py --configure-solr
  python3 run_pipeline.py --solr-url http://localhost:8983/solr/RamenProject
        """
    )
    
    parser.add_argument('--skip-scrape', action='store_true',
                       help='Skip scraping step')
    parser.add_argument('--skip-clean', action='store_true',
                       help='Skip cleaning step')
    parser.add_argument('--skip-index', action='store_true',
                       help='Skip indexing step')
    parser.add_argument('--start-frontend', action='store_true',
                       help='Start frontend services after completion')
    parser.add_argument('--configure-solr', action='store_true',
                       help='Configure Solr schema (synonyms and single-char matching) before indexing')
    parser.add_argument('--solr-url', default='http://localhost:8983/solr/RamenProject',
                       help='Solr URL (default: http://localhost:8983/solr/RamenProject)')
    parser.add_argument('--use-labse', action='store_true',
                       help='Enable LaBSE semantic embeddings (requires sentence-transformers)')
    
    args = parser.parse_args()
    
    runner = PipelineRunner(
        skip_scrape=args.skip_scrape,
        skip_clean=args.skip_clean,
        skip_index=args.skip_index,
        start_frontend=args.start_frontend,
        configure_solr=args.configure_solr,
        solr_url=args.solr_url,
        use_labse=args.use_labse
    )
    
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
