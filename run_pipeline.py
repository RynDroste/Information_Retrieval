#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete data processing pipeline script
Executes: scraping -> cleaning -> indexing -> start services
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path

# Import modules
from scraper import RamenScraper
from data_cleaner import DataCleaner
from solr_indexer import SolrIndexer


class PipelineRunner:
    def __init__(self, skip_scrape=False, skip_clean=False, skip_index=False, 
                 start_frontend=False, solr_url='http://localhost:8983/solr/afuri_menu'):
        self.skip_scrape = skip_scrape
        self.skip_clean = skip_clean
        self.skip_index = skip_index
        self.start_frontend = start_frontend
        self.solr_url = solr_url
        self.errors = []
        
    def print_header(self, step_name):
        """Print step header"""
        print("\n" + "=" * 80)
        print(f"📋 {step_name}")
        print("=" * 80)
    
    def step1_scrape(self):
        """Step 1: Scrape data"""
        if self.skip_scrape:
            print("\n⏭️  Skipping scrape step")
            return True
            
        self.print_header("Step 1/3: Scraping website data")
        
        try:
            scraper = RamenScraper()
            
            # Scrape menu page
            scraper.scrape_menu_page()
            
            # Scrape store information
            scraper.scrape_store_information()
            
            # Scrape brand information
            scraper.scrape_brand_info()
            
            # Save data
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
        """Step 2: Clean data"""
        if self.skip_clean:
            print("\n⏭️  Skipping clean step")
            return True
            
        self.print_header("Step 2/3: Cleaning data")
        
        # Check if input file exists
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
    
    def step3_index(self):
        """Step 3: Index to Solr"""
        if self.skip_index:
            print("\n⏭️  Skipping index step")
            return True
            
        self.print_header("Step 3/3: Indexing to Solr")
        
        # Check if input file exists
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
        """Step 4: Start frontend services (optional)"""
        if not self.start_frontend:
            return True
            
        self.print_header("Starting frontend services")
        
        print("Starting Solr proxy server and frontend server...")
        print("📱 Frontend URL: http://localhost:8000/frontend/")
        print("Press Ctrl+C to stop services\n")
        
        try:
            # Use start_frontend.sh script to start services
            script_path = Path(__file__).parent / 'start_frontend.sh'
            if script_path.exists():
                subprocess.run(['bash', str(script_path)])
            else:
                print("⚠️  start_frontend.sh not found, starting services manually...")
                # Manual startup
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
        """Run complete pipeline"""
        print("\n" + "=" * 80)
        print("🚀 AFURI Data Processing Pipeline")
        print("=" * 80)
        print(f"Working directory: {os.getcwd()}")
        print(f"Solr URL: {self.solr_url}")
        print("=" * 80)
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        success = True
        
        # Step 1: Scrape
        if not self.step1_scrape():
            success = False
            if not self.skip_scrape:
                print("\n❌ Pipeline failed at scraping step, stopping execution")
                return False
        
        # Step 2: Clean
        if not self.step2_clean():
            success = False
            if not self.skip_clean:
                print("\n❌ Pipeline failed at cleaning step, stopping execution")
                return False
        
        # Step 3: Index
        if not self.step3_index():
            success = False
            if not self.skip_index:
                print("\n❌ Pipeline failed at indexing step, stopping execution")
                return False
        
        # Step 4: Start services (optional)
        if success and self.start_frontend:
            self.step4_start_services()
        
        # Print summary
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
  # Run complete pipeline
  python3 run_pipeline.py
  
  # Skip scraping, only clean and index
  python3 run_pipeline.py --skip-scrape
  
  # Only index (assuming cleaned data exists)
  python3 run_pipeline.py --skip-scrape --skip-clean
  
  # Run complete pipeline and start frontend services
  python3 run_pipeline.py --start-frontend
  
  # Use custom Solr URL
  python3 run_pipeline.py --solr-url http://localhost:8983/solr/afuri_menu
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
    parser.add_argument('--solr-url', default='http://localhost:8983/solr/afuri_menu',
                       help='Solr URL (default: http://localhost:8983/solr/afuri_menu)')
    
    args = parser.parse_args()
    
    runner = PipelineRunner(
        skip_scrape=args.skip_scrape,
        skip_clean=args.skip_clean,
        skip_index=args.skip_index,
        start_frontend=args.start_frontend,
        solr_url=args.solr_url
    )
    
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

