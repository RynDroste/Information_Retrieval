#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import subprocess
import time
import json
import shutil
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
                         "minGramSize": "1", 
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
                         "minGramSize": "1", 
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
    
    def update_fields(self):
        fields = ["title", "content", "menu_item", "ingredients"]
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
                 solr_url='http://localhost:8983/solr/RamenProject'):
        self.skip_scrape = skip_scrape
        self.skip_clean = skip_clean
        self.skip_index = skip_index
        self.start_frontend = start_frontend
        self.configure_solr = configure_solr
        self.solr_url = solr_url
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
            
            scraper.scrape_menu_page()
            
            scraper.scrape_store_information()
            
            scraper.scrape_brand_info()
            
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
            indexer = SolrIndexer(solr_url=self.solr_url)
            
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
    
    def step4_start_services(self):
        if not self.start_frontend:
            return True
            
        self.print_header("Starting frontend services")
        
        print("Starting Solr proxy server and frontend server...")
        print("📱 Frontend URL: http://localhost:8000/frontend/")
        print("Press Ctrl+C to stop services\n")
        
        try:
            script_path = Path(__file__).parent / 'start_frontend.sh'
            if script_path.exists():
                subprocess.run(['bash', str(script_path)])
            else:
                print("⚠️  start_frontend.sh not found, starting services manually...")
                import threading
                
                def start_proxy():
                    from solr_proxy import main as proxy_main
                    proxy_main()
                
                def start_frontend():
                    subprocess.run(['python3', '-m', 'http.server', '8000'])
                
                proxy_thread = threading.Thread(target=start_proxy, daemon=True)
                proxy_thread.start()
                time.sleep(1)
                start_frontend()
                
        except KeyboardInterrupt:
            print("\n\nServices stopped")
        except Exception as e:
            error_msg = f"Error starting services: {str(e)}"
            print(f"\n✗ {error_msg}")
            self.errors.append(error_msg)
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
    
    args = parser.parse_args()
    
    runner = PipelineRunner(
        skip_scrape=args.skip_scrape,
        skip_clean=args.skip_clean,
        skip_index=args.skip_index,
        start_frontend=args.start_frontend,
        configure_solr=args.configure_solr,
        solr_url=args.solr_url
    )
    
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
