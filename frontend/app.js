class ArticleSearch {
    constructor() {
        this.filteredArticles = [];
        this.activeFilters = { section: null, category: null, tag: null, priceRange: null };
        this.solrUrl = 'http://localhost:8888/solr/RamenProject/select';
        this.semanticApiUrl = 'http://localhost:8889';
        this.semanticSearchAvailable = false;
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.checkSemanticSearchAvailability();
        await this.displayStats();
        await this.loadAllTags();
        this.updateActiveFiltersDisplay();
    }

    async checkSemanticSearchAvailability() {
        try {
            const response = await fetch(`${this.semanticApiUrl}/semantic/status`);
            if (response.ok) {
                const data = await response.json();
                this.semanticSearchAvailable = data.available || false;
                if (this.semanticSearchAvailable) {
                    console.log('%c✓ Semantic search available', 'color: green; font-weight: bold;', `(${data.embeddings_count} embeddings)`);
                    console.log('  → Hybrid search enabled: Keyword (60%) + Semantic (40%)');
                } else {
                    console.log('%c⚠ Semantic search API responded but is not available', 'color: orange;');
                    console.log('  → Using keyword search only');
                }
            } else {
                console.log('%c⚠ Semantic search API not responding', 'color: orange;');
                console.log('  → Using keyword search only');
                this.semanticSearchAvailable = false;
            }
        } catch (error) {
            console.log('%cℹ Semantic search API not available', 'color: blue;');
            console.log('  → Using keyword search only');
            console.log('  → To enable semantic search:');
            console.log('    1. Install: pip3 install sentence-transformers numpy torch');
            console.log('    2. Run: python3 run_pipeline.py --use-labse --configure-solr');
            console.log('    3. Start: bash start_frontend.sh true');
            this.semanticSearchAvailable = false;
        }
    }

    setupEventListeners() {
        document.getElementById('searchBtn').addEventListener('click', () => this.performSearch());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        document.getElementById('sortBy').addEventListener('change', () => {
            if (this.filteredArticles.length > 0) {
                this.sortArticles();
                this.displayResults();
            }
        });
        const clearBtn = document.getElementById('clearFilters');
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearAllFilters());
    }

    getFieldValue(field, defaultValue = '') {
        if (!field) return defaultValue;
        return Array.isArray(field) ? (field.length > 0 ? String(field[0]) : defaultValue) : String(field);
    }

    getFieldArray(field, defaultValue = []) {
        if (!field) return defaultValue;
        return Array.isArray(field) ? field.map(String) : [String(field)];
    }

    /**
     * Calculate Keyword Score from Solr score (normalized to 0-1 range)
     * This is independent of semantic search
     * 
     * @param {number} solrScore - Original Solr score
     * @returns {number} Normalized keyword score (0-1)
     */
    calculateKeywordScore(solrScore) {
        // Handle different types and formats
        let score = solrScore;
        
        // Convert string to number if needed
        if (typeof score === 'string') {
            score = parseFloat(score);
            if (isNaN(score)) {
                console.warn(`[calculateKeywordScore] Invalid score string: ${solrScore}`);
                return 0.0;
            }
        }
        
        // Handle null, undefined, or zero
        if (score === null || score === undefined || score === 0) {
            return 0.0;
        }
        
        // Normalize Solr score to 0-1 range
        // If score is very large (>100), divide by 100, otherwise divide by 10
        if (score > 100) {
            return Math.min(1.0, score / 100.0);
        } else {
            return Math.min(1.0, score / 10.0);
        }
    }

    /**
     * Add keyword_score to all documents based on Solr score
     * This ensures keyword_score is always available, regardless of semantic search
     * 
     * @param {Array} docs - Documents from Solr
     * @returns {Array} Documents with keyword_score added
     */
    addKeywordScores(docs) {
        return docs.map((doc, index) => {
            // Get Solr score - try different possible field names
            let solrScore = doc.score;
            if (solrScore === undefined || solrScore === null) {
                solrScore = doc._score || doc['score'] || 0;
            }
            
            const keywordScore = this.calculateKeywordScore(solrScore);
            
            // Debug: log first few documents
            if (index < 3) {
                console.log(`[Debug Keyword Score] Document ${index + 1}: ${doc.title || doc.menu_item || 'N/A'}`);
                console.log(`  Raw doc.score: ${doc.score} (type: ${typeof doc.score})`);
                console.log(`  Using solrScore: ${solrScore} (type: ${typeof solrScore})`);
                console.log(`  Calculated keyword_score: ${keywordScore}`);
                console.log(`  Final doc.keyword_score: ${keywordScore}`);
            }
            
            return {
                ...doc,
                keyword_score: keywordScore
            };
        });
    }

    buildQuery(searchText = '') {
        const queryParts = [];
        if (this.activeFilters.section) queryParts.push(`section:"${this.activeFilters.section}"`);
        if (this.activeFilters.category) {
            const val = this.activeFilters.category.trim().replace(/[+\-&|!(){}[\]^"~*?:\\]/g, '\\$&');
            queryParts.push(`menu_category:"${val}"`);
        }
        if (this.activeFilters.tag) {
            queryParts.push(`tags:"${this.activeFilters.tag.replace(/"/g, '\\"')}"`);
        }
        if (this.activeFilters.priceRange) {
            const val = this.activeFilters.priceRange.trim().replace(/[+\-&|!(){}[\]^"~*?:\\]/g, '\\$&');
            queryParts.push(`price_range:"${val}"`);
        }
        const searchQuery = searchText ? searchText.replace(/[+\-&|!(){}[\]^"~*?:\\]/g, '\\$&') : '';
        if (queryParts.length === 0) return searchQuery || '*:*';
        const filterQuery = queryParts.join(' AND ');
        return searchQuery ? `(${filterQuery}) AND (${searchQuery})` : filterQuery;
    }

    async performSearch() {
        const query = document.getElementById('searchInput').value.trim();
        await this.executeSearch(this.buildQuery(query));
    }

    async performSearchWithFilters() {
        const query = document.getElementById('searchInput').value.trim();
        await this.executeSearch(this.buildQuery(query));
    }

    async executeSearch(finalQuery) {
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const noResults = document.getElementById('noResults');
        loading.style.display = 'block';
        results.innerHTML = '';
        noResults.style.display = 'none';

        try {
            await this.searchSolr(finalQuery);
            await this.loadAllTags();
        } catch (error) {
            this.showError(error, results);
        } finally {
            loading.style.display = 'none';
        }
    }

    showError(error, results) {
        console.error('Search error:', error);
        let msg = 'Error performing search. ';
        if (error.message.includes('fetch') || error.message.includes('Failed to fetch')) {
            msg += 'Cannot connect to Solr server. Please make sure Solr is running on http://localhost:8983';
        } else if (error.message.includes('CORS')) {
            msg += 'CORS error. Please check Solr CORS configuration.';
        } else {
            msg += error.message || 'Please check the browser console for details.';
        }
        results.innerHTML = `<div class="no-results"><p>${msg}</p><p style="font-size: 12px; color: #6c757d; margin-top: 10px;">If Solr is running, check browser console (F12) for more details.</p></div>`;
    }

    parseDocs(docs) {
        return docs.map(doc => ({
            id: doc.id || '',  // Include ID for detail page navigation
            url: this.getFieldValue(doc.url),
            title: this.getFieldValue(doc.title),
            content: this.getFieldValue(doc.content),
            section: this.getFieldValue(doc.section),
            menu_item: this.getFieldValue(doc.menu_item),
            menu_category: this.getFieldValue(doc.menu_category),
            introduction: this.getFieldValue(doc.introduction),
            store_name: this.getFieldValue(doc.store_name),
            date: this.getFieldValue(doc.date),
            price: this.getFieldValue(doc.price),
            price_range: this.getFieldValue(doc.price_range),
            tags: this.getFieldArray(doc.tags)
        }));
    }

    /**
     * Universal search algorithm that intelligently combines multiple keywords
     * Supports any combination of brand, category, type, and other keywords
     */
    buildBoostQuery(query) {
        const queryLower = query.toLowerCase().trim();
        const words = queryLower.split(/\s+/).filter(w => w.length > 0);
        
        // Define keyword patterns with their types and boost rules
        const keywordPatterns = {
            // Brand keywords
            brand: {
                keywords: ['afuri'],
                boost: {
                    solo: { 'section:"Brand Information"': 7.0, 'section:"Store Information"': 6.5 },
                    combined: { 'section:"Brand Information"': 5.5, 'section:"Store Information"': 5.0 }
                }
            },
            // Category keywords (menu categories)
            category: {
                keywords: [
                    { patterns: ['drink', 'drinks', 'beverage', 'beverages'], target: 'menu_category:"Drinks"' },
                    { patterns: ['ramen'], target: 'menu_category:"Ramen"' },
                    { patterns: ['noodle', 'noodles'], target: 'menu_category:"Noodles"' },
                    { patterns: ['tsukemen'], target: 'menu_category:"Tsukemen"' },
                    { patterns: ['side', 'side dish', 'side dishes'], target: 'menu_category:"Side Dishes"' },
                    { patterns: ['soup'], target: 'menu_category:"Soup"' },
                    { patterns: ['chi-yu', 'chiyu'], target: 'menu_category:"Chi-yu"' }
                ],
                boost: {
                    solo: 7.0,
                    combined: 7.0  // Categories always get high priority
                }
            },
            // Type keywords (section types)
            type: {
                keywords: [
                    { patterns: ['store', 'stores', 'location', 'locations', 'shop', 'shops'], target: 'section:"Store Information"' },
                    { patterns: ['brand', 'brands', 'company'], target: 'section:"Brand Information"' },
                    { patterns: ['menu', 'menus', 'item', 'items', 'product', 'products', 'food', 'foods', 'dish', 'dishes'], target: 'section:"Menu"' }
                ],
                boost: {
                    solo: 6.0,
                    combined: 6.5  // Increased for combined queries to prioritize Menu over Brand
                }
            }
        };
        
        // Detect all matched keywords by type
        const detected = {
            brand: null,
            category: [],
            type: []
        };
        
        // Check brand keywords
        for (const brandKeyword of keywordPatterns.brand.keywords) {
            if (queryLower.includes(brandKeyword)) {
                detected.brand = brandKeyword;
                break;
            }
        }
        
        // Check category keywords (check multi-word patterns first, then single words)
        for (const categoryDef of keywordPatterns.category.keywords) {
            for (const pattern of categoryDef.patterns) {
                // Check for multi-word patterns
                if (pattern.includes(' ')) {
                    if (queryLower.includes(pattern)) {
                        detected.category.push({ target: categoryDef.target, pattern });
                        break;
                    }
                } else {
                    // Check for single word patterns (as whole word or part of word)
                    if (words.includes(pattern) || queryLower.includes(pattern)) {
                        detected.category.push({ target: categoryDef.target, pattern });
                        break;
                    }
                }
            }
        }
        
        // Check type keywords
        for (const typeDef of keywordPatterns.type.keywords) {
            for (const pattern of typeDef.patterns) {
                if (words.includes(pattern) || queryLower.includes(pattern)) {
                    detected.type.push({ target: typeDef.target, pattern });
                    break;
                }
            }
        }
        
        // Build boost query based on detected keywords
        const bqParts = [];
        const hasMultipleTypes = (detected.category.length > 0 ? 1 : 0) + 
                                 (detected.type.length > 0 ? 1 : 0) + 
                                 (detected.brand ? 1 : 0) > 1;
        
        // Priority 1: Category keywords (highest priority when present)
        if (detected.category.length > 0) {
            const boost = hasMultipleTypes ? keywordPatterns.category.boost.combined : keywordPatterns.category.boost.solo;
            detected.category.forEach(cat => {
                bqParts.push(`${cat.target}^${boost}`);
            });
        }
        
        // Special handling for "yuzu ramen" - boost Ramen category and exact phrase matches
        if (queryLower.includes('yuzu') && queryLower.includes('ramen')) {
            bqParts.push('menu_category:"Ramen"^8.0');
        }
        
        // Priority 2: Type keywords (Menu section should have higher priority than Brand when both are present)
        // Check if Menu type is detected
        const menuTypeDetected = detected.type.some(t => t.target === 'section:"Menu"');
        if (detected.type.length > 0) {
            const boost = hasMultipleTypes ? keywordPatterns.type.boost.combined : keywordPatterns.type.boost.solo;
            detected.type.forEach(type => {
                // If Menu type is detected along with brand, give Menu much higher boost
                if (type.target === 'section:"Menu"' && detected.brand && hasMultipleTypes) {
                    bqParts.push(`${type.target}^9.0`);  // Much higher boost for Menu when combined with brand
                } else {
                    bqParts.push(`${type.target}^${boost}`);
                }
            });
        }
        
        // Priority 3: Brand keywords
        if (detected.brand) {
            const boostConfig = hasMultipleTypes ? keywordPatterns.brand.boost.combined : keywordPatterns.brand.boost.solo;
            Object.entries(boostConfig).forEach(([target, boost]) => {
                // Reduce brand boost when Menu type is also detected
                if (menuTypeDetected && hasMultipleTypes && target === 'section:"Brand Information"') {
                    bqParts.push(`${target}^2.0`);  // Much lower boost for Brand when Menu is present
                } else {
                    // When searching for "brand" alone, give very high boost to Brand Information
                    if (!hasMultipleTypes && target === 'section:"Brand Information"') {
                        bqParts.push(`${target}^8.0`);  // Very high boost for "brand" query
                    } else {
                        bqParts.push(`${target}^${boost}`);
                    }
                }
            });
        }
        
        return bqParts.length > 0 ? bqParts.join(' ') : '';
    }

    async searchSolr(query) {
        const queryLower = query.toLowerCase().trim();
        const originalQuery = document.getElementById('searchInput').value.trim();
        const bq = this.buildBoostQuery(originalQuery);
        
        const params = new URLSearchParams({
            q: query,
            defType: 'edismax',
            qf: 'title^2.0 content^1.5 menu_item^2.5 introduction^1.0 menu_category^2.0 store_name^3.0',
            pf: 'title^5.0 menu_item^5.0 store_name^6.0',
            ps: '2',
            mm: '2<75% 3<50%',
            rows: 1000,
            wt: 'json',
            fl: '*,score'  // Ensure score field is returned
        });
        
        if (bq) params.append('bq', bq);

        try {
            const response = await fetch(`${this.solrUrl}?${params}`);
            if (!response.ok) throw new Error(`Solr request failed: ${response.status} ${response.statusText}`);
            
            const data = await response.json();
            if (data.response?.numFound === 0 && query.includes('menu_category:"')) {
                const altResult = await this.tryAlternativeQueries(query);
                if (altResult) return;
            }

            let docs = data.response?.docs || [];
            
            // Calculate keyword_score for all documents (independent of semantic search)
            docs = this.addKeywordScores(docs);
            
            // Log Solr keyword search results
            if (docs.length > 0) {
                console.group(`%c🔍 Solr Keyword Search Results for: "${originalQuery}"`, 'color: blue; font-weight: bold;');
                console.table(docs.slice(0, 10).map((doc, index) => ({
                    Rank: index + 1,
                    Title: this.getFieldValue(doc.title) || this.getFieldValue(doc.menu_item) || 'N/A',
                    Section: this.getFieldValue(doc.section) || 'N/A',
                    'Solr Score': doc.score ? doc.score.toFixed(3) : 'N/A',
                    'Keyword Score': (doc.keyword_score !== undefined && doc.keyword_score !== null) ? doc.keyword_score.toFixed(3) : 'N/A'
                })));
                console.groupEnd();
            }
            
            // If semantic search is available and we have results, rerank using semantic search
            if (this.semanticSearchAvailable && docs.length > 0 && originalQuery.trim()) {
                try {
                    console.log(`%c🔍 Using semantic search for: "${originalQuery}"`, 'color: purple; font-weight: bold;');
                    docs = await this.rerankWithSemanticSearch(originalQuery, docs);
                    
                    // Apply section-based boost after semantic reranking
                    // If query contains "food" or menu-related keywords, boost Menu section
                    const queryLower = originalQuery.toLowerCase().trim();
                    const hasFoodKeyword = /\b(food|foods|menu|menus|item|items|product|products|dish|dishes)\b/.test(queryLower);
                    const hasBrandKeyword = /\b(afuri)\b/.test(queryLower);
                    const isBrandOnlyQuery = /\b(brand|brands)\b/.test(queryLower) && !hasFoodKeyword && !hasBrandKeyword;
                    
                    // Boost Brand Information when searching for "brand" alone
                    if (isBrandOnlyQuery) {
                        docs = docs.map(doc => {
                            const section = this.getFieldValue(doc.section);
                            const originalScore = doc.score || 0;
                            if (section === 'Brand Information') {
                                return { ...doc, score: originalScore * 2.0 };  // Boost Brand by 100%
                            } else if (section === 'Menu') {
                                return { ...doc, score: originalScore * 0.5 };  // Reduce Menu by 50%
                            }
                            return doc;
                        });
                        // Re-sort by adjusted score
                        docs.sort((a, b) => (b.score || 0) - (a.score || 0));
                        console.log(`%c⚡ Post-processing boost applied for "brand" query (Brand ×2.0, Menu ×0.5)`, 'color: orange;');
                    } else if (hasFoodKeyword && hasBrandKeyword) {
                        // Boost Menu section and demote Brand Information
                        const beforeBoost = docs.slice(0, 5).map(d => ({
                            title: this.getFieldValue(d.title),
                            section: this.getFieldValue(d.section),
                            score: d.score
                        }));
                        
                        docs = docs.map(doc => {
                            const section = this.getFieldValue(doc.section);
                            const originalScore = doc.score || 0;
                            if (section === 'Menu') {
                                return { ...doc, score: originalScore * 1.5 };  // Boost Menu by 50%
                            } else if (section === 'Brand Information') {
                                return { ...doc, score: originalScore * 0.3 };  // Reduce Brand by 70%
                            }
                            return doc;
                        });
                        // Re-sort by adjusted score
                        docs.sort((a, b) => (b.score || 0) - (a.score || 0));
                        
                        // Log post-processing boost
                        console.log(`%c⚡ Post-processing boost applied (Menu ×1.5, Brand ×0.3)`, 'color: orange;');
                        const afterBoost = docs.slice(0, 5).map(d => ({
                            title: this.getFieldValue(d.title),
                            section: this.getFieldValue(d.section),
                            score: d.score
                        }));
                        console.log('Before Boost:', beforeBoost);
                        console.log('After Boost:', afterBoost);
                    }
                    
                    // Log final ranking
                    console.group(`%c✅ Final Ranking (Top 10)`, 'color: green; font-weight: bold;');
                    console.table(docs.slice(0, 10).map((doc, index) => ({
                        Rank: index + 1,
                        Title: this.getFieldValue(doc.title) || this.getFieldValue(doc.menu_item) || 'N/A',
                        Section: this.getFieldValue(doc.section) || 'N/A',
                        'Final Score': (doc.score !== undefined && doc.score !== null) ? doc.score.toFixed(3) : 'N/A',
                        'Keyword Score': (doc.keyword_score !== undefined && doc.keyword_score !== null) ? doc.keyword_score.toFixed(3) : 'N/A',
                        'Semantic Score': (doc.semantic_score !== undefined && doc.semantic_score !== null) ? doc.semantic_score.toFixed(3) : 'N/A'
                    })));
                    console.groupEnd();
                    
                    console.log(`%c✓ Semantic reranking completed`, 'color: green;', `(${docs.length} results)`);
                } catch (semanticError) {
                    console.warn('%c⚠ Semantic search reranking failed, using Solr results', 'color: orange;', semanticError);
                }
            } else if (docs.length > 0 && originalQuery.trim()) {
                console.log(`%c🔍 Using keyword search only for: "${originalQuery}"`, 'color: blue;');
                
                // Log final ranking with keyword scores (even without semantic search)
                console.group(`%c✅ Final Ranking (Top 10)`, 'color: green; font-weight: bold;');
                console.table(docs.slice(0, 10).map((doc, index) => ({
                    Rank: index + 1,
                    Title: this.getFieldValue(doc.title) || this.getFieldValue(doc.menu_item) || 'N/A',
                    Section: this.getFieldValue(doc.section) || 'N/A',
                    'Final Score': (doc.score !== undefined && doc.score !== null) ? doc.score.toFixed(3) : 'N/A',
                    'Keyword Score': (doc.keyword_score !== undefined && doc.keyword_score !== null) ? doc.keyword_score.toFixed(3) : 'N/A',
                    'Semantic Score': 'N/A (not used)'
                })));
                console.groupEnd();
            }

            if (docs.length > 0) {
                this.filteredArticles = this.parseDocs(docs);
            } else {
                this.filteredArticles = [];
            }
            this.sortArticles();
            this.displayResults();
            this.updateActiveFiltersDisplay();
        } catch (error) {
            console.error('Solr search error:', error);
            if (error.message.includes('fetch') || error.message.includes('Failed to fetch') || error.name === 'TypeError') {
                const msg = error.message || error.toString();
                if (msg.includes('CORS') || msg.includes('cross-origin')) {
                    throw new Error('CORS error: Browser blocked the request. Solr may need CORS configuration.');
                }
                throw new Error('Cannot connect to Solr server. Please make sure Solr is running on http://localhost:8983. Error: ' + msg);
            }
            throw error;
        }
    }

    async rerankWithSemanticSearch(query, candidates) {
        // Prepare candidates with id and score for semantic API
        const candidatesForAPI = candidates.map((doc, index) => ({
            id: doc.id || `doc_${index}`,
            title: this.getFieldValue(doc.title),
            menu_item: this.getFieldValue(doc.menu_item),
            content: this.getFieldValue(doc.content),
            menu_category: this.getFieldValue(doc.menu_category),
            score: doc.score || 0,
            ...doc
        }));

        try {
            const response = await fetch(`${this.semanticApiUrl}/semantic/rerank`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    candidates: candidatesForAPI,
                    top_k: 100,
                    keyword_weight: 0.5,  // Reduced from 0.6 to give more weight to semantic understanding
                    semantic_weight: 0.5  // Increased from 0.4 to better understand "food" context
                })
            });

            if (!response.ok) {
                throw new Error(`Semantic API request failed: ${response.status}`);
            }

            const data = await response.json();
            if (data.success && data.results && data.results.length > 0) {
                // Log detailed scores for debugging
                console.group(`%c📊 Semantic Search Scores for: "${query}"`, 'color: purple; font-weight: bold;');
                console.table(data.results.slice(0, 10).map((result, index) => ({
                    Rank: index + 1,
                    Title: result.title || result.menu_item || 'N/A',
                    Section: result.section || 'N/A',
                    'Keyword Score': (result.keyword_score !== undefined && result.keyword_score !== null) ? result.keyword_score.toFixed(3) : 'N/A',
                    'Semantic Score': (result.semantic_score !== undefined && result.semantic_score !== null) ? result.semantic_score.toFixed(3) : 'N/A',
                    'Combined Score': (result.combined_score !== undefined && result.combined_score !== null) ? result.combined_score.toFixed(3) : 'N/A'
                })));
                console.groupEnd();
                
                // Map reranked results back to original doc format
                const rerankedDocs = data.results.map(result => {
                    // Find original doc by id
                    const originalDoc = candidates.find(doc => doc.id === result.id);
                    if (originalDoc) {
                        // Calculate keyword_score from original Solr score (always from Solr, not from semantic API)
                        // This ensures keyword_score is independent of semantic search
                        const keywordScore = this.calculateKeywordScore(originalDoc.score || 0);
                        
                        // Get semantic_score (may be 0 for docs without embeddings)
                        const semanticScore = (result.semantic_score !== undefined && result.semantic_score !== null) 
                            ? result.semantic_score 
                            : 0.0;
                        
                        // Update score with combined score and preserve detailed scores
                        const rerankedDoc = {
                            ...originalDoc,
                            score: result.combined_score || result.score || originalDoc.score,
                            keyword_score: keywordScore,
                            semantic_score: semanticScore,
                            combined_score: result.combined_score || result.score || originalDoc.score
                        };
                        
                        // Debug: log first few documents to verify scores
                        const currentIndex = data.results.indexOf(result);
                        if (currentIndex < 3) {
                            console.log(`📝 Reranked doc [${currentIndex + 1}]: ${rerankedDoc.title || rerankedDoc.menu_item || 'N/A'}`);
                            console.log(`   keyword_score: ${rerankedDoc.keyword_score} (from API: ${result.keyword_score})`);
                            console.log(`   semantic_score: ${rerankedDoc.semantic_score} (from API: ${result.semantic_score})`);
                            console.log(`   combined_score: ${rerankedDoc.combined_score}`);
                        }
                        
                        return rerankedDoc;
                    }
                    return null;
                }).filter(doc => doc !== null);

                return rerankedDocs.length > 0 ? rerankedDocs : candidates;
            }
        } catch (error) {
            console.error('Semantic reranking error:', error);
            throw error;
        }

        return candidates;
    }

    async tryAlternativeQueries(query) {
        const match = query.match(/menu_category:"([^"]+)"/);
        if (!match) return false;
        
        const categoryValue = match[1];
        const altQueries = [
            query.replace(/menu_category:"([^"]+)"/g, 'menu_category:$1'),
            query.replace(/menu_category:"([^"]+)"/g, `menu_category:*${categoryValue}*`),
            query.replace(/menu_category:"([^"]+)"/g, `menu_category:${categoryValue.toLowerCase()}`),
            query.replace(/menu_category:"([^"]+)"/g, `menu_category:${categoryValue.toUpperCase()}`)
        ];

        for (const testQuery of altQueries) {
            try {
                const params = new URLSearchParams({ q: testQuery, rows: 1000, wt: 'json' });
                const response = await fetch(`${this.solrUrl}?${params}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.response?.numFound > 0) {
                        this.filteredArticles = this.parseDocs(data.response.docs);
                        this.sortArticles();
                        this.displayResults();
                        this.updateActiveFiltersDisplay();
                        await this.loadAllTags();
                        return true;
                    }
                }
            } catch (e) {
                console.error(`Alternative query failed:`, e);
            }
        }
        return false;
    }

    sortArticles() {
        const sortBy = document.getElementById('sortBy').value;
        if (sortBy === 'title-asc') {
            this.filteredArticles.sort((a, b) => 
                (a.title || '').toLowerCase().localeCompare((b.title || '').toLowerCase())
            );
        } else if (sortBy === 'category') {
            this.filteredArticles.sort((a, b) => {
                const catA = (a.menu_category || '').toLowerCase();
                const catB = (b.menu_category || '').toLowerCase();
                return catA !== catB ? catA.localeCompare(catB) : 
                    (a.title || '').toLowerCase().localeCompare((b.title || '').toLowerCase());
            });
        }
    }

    renderTags(tags, filterType) {
        return tags
            .filter(tag => tag.toLowerCase() !== 'others')  // Filter out "others" tag
            .map(tag => {
                return `<span class="tag-badge clickable-tag" 
                        data-filter-type="${filterType}" data-filter-value="${this.escapeHtml(tag)}" 
                        title="Click to filter #${this.escapeHtml(tag)}">#${this.escapeHtml(tag)}</span>`;
            }).join('');
    }

    displayResults() {
        const results = document.getElementById('results');
        const noResults = document.getElementById('noResults');

        if (this.filteredArticles.length === 0) {
            results.innerHTML = '';
            noResults.style.display = 'block';
            return;
        }

        noResults.style.display = 'none';
        const query = document.getElementById('searchInput').value.trim().toLowerCase();
        const queryWords = query ? query.split(/\s+/).filter(w => w.length > 0) : [];

        results.innerHTML = this.filteredArticles.map(article => {
            const { section, menuCategory, tags, introduction } = {
                section: article.section || '',
                menuCategory: article.menu_category || '',
                tags: article.tags || [],
                introduction: article.introduction || ''
            };

            let categoryLine = '', tagsLine = '', introductionLine = '';
            
            if (section === 'Menu' && menuCategory) {
                const isSectionActive = this.activeFilters.section === 'Menu';
                const isCategoryActive = this.activeFilters.category === menuCategory;
                categoryLine = `<div class="category-line">
                    <span class="tag-badge tag-menu clickable-tag ${isSectionActive ? 'active' : ''}" 
                          data-filter-type="section" data-filter-value="Menu">Menu</span>
                    <span class="category-badge category-${menuCategory.toLowerCase().replace(' ', '-')} clickable-tag ${isCategoryActive ? 'active' : ''}" 
                          data-filter-type="category" data-filter-value="${this.escapeHtml(menuCategory)}">${this.escapeHtml(menuCategory)}</span>
                </div>`;
                if (tags.length > 0) tagsLine = `<div class="tags-line">${this.renderTags(tags, 'tag')}</div>`;
                if (introduction) introductionLine = `<div class="ingredients-line"><span class="section-label">Introduction:</span><span class="ingredients-text">${this.escapeHtml(introduction)}</span></div>`;
            } else if (section === 'Store Information' || section === 'Brand Information') {
                const label = section === 'Store Information' ? 'Store' : 'Brand';
                const badgeClass = section === 'Store Information' ? 'tag-store' : 'tag-brand';
                const isSectionActive = this.activeFilters.section === section;
                if (tags.length > 0) {
                    tagsLine = `<div class="tags-line">
                        <span class="tag-badge ${badgeClass} clickable-tag ${isSectionActive ? 'active' : ''}" 
                              data-filter-type="section" data-filter-value="${section}">${label}</span>
                        ${this.renderTags(tags, 'tag')}
                    </div>`;
                }
            }

            const priceDisplay = article.price ? `<span class="product-price">${this.escapeHtml(article.price)}</span>` : '';
            
            // Create detail page link using article ID
            const detailLink = article.id ? `detail.html?id=${encodeURIComponent(article.id)}` : '#';
            
            return `<div class="article-card">
                <div class="article-header">
                    <h2><a href="${detailLink}">${this.highlightText(article.title, queryWords)}</a></h2>
                    ${priceDisplay}
                </div>
                ${categoryLine}${tagsLine}${introductionLine}
                <div class="article-meta">
                    ${article.menu_item && article.menu_item !== article.title ? `<span>🍜 ${article.menu_item}</span>` : ''}
                    ${article.store_name ? `<span>📍 ${article.store_name}</span>` : ''}
                    ${article.date ? `<span>📅 ${this.formatDate(article.date)}</span>` : ''}
                </div>
                <div class="article-content">${this.getContentPreview(article.content, queryWords, 300)}</div>
            </div>`;
        }).join('');
        
        this.attachTagClickListeners();
    }
    
    attachTagClickListeners() {
        document.querySelectorAll('.clickable-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleTagClick(tag.dataset.filterType, tag.dataset.filterValue);
            });
        });
    }
    
    handleTagClick(filterType, filterValue) {
        this.activeFilters[filterType] = this.activeFilters[filterType] === filterValue ? null : filterValue;
        this.updateActiveFiltersDisplay();
        this.performSearchWithFilters();
    }
    
    clearAllFilters() {
        this.activeFilters = { section: null, category: null, tag: null, priceRange: null };
        this.updateActiveFiltersDisplay();
        this.performSearchWithFilters();
    }
    
    updateActiveFiltersDisplay() {
        const activeFiltersDiv = document.getElementById('activeFilters');
        const filterTagsDiv = document.getElementById('filterTags');
        const hasFilters = this.activeFilters.section || this.activeFilters.category || this.activeFilters.tag || this.activeFilters.priceRange;
        
        if (!hasFilters) {
            activeFiltersDiv.style.display = 'none';
            return;
        }

        activeFiltersDiv.style.display = 'flex';
        filterTagsDiv.innerHTML = '';
        
        ['section', 'category', 'tag', 'priceRange'].forEach(type => {
            if (this.activeFilters[type]) {
                const tag = document.createElement('span');
                tag.className = 'filter-tag';
                let displayText = '';
                if (type === 'tag') {
                    displayText = `#${this.activeFilters[type]}`;
                } else if (type === 'section') {
                    displayText = this.getSectionLabel(this.activeFilters[type]);
                } else if (type === 'priceRange') {
                    displayText = `💰 ${this.activeFilters[type]}`;
                } else {
                    displayText = this.activeFilters[type];
                }
                tag.textContent = displayText;
                tag.addEventListener('click', () => {
                    this.activeFilters[type] = null;
                    this.updateActiveFiltersDisplay();
                    this.performSearchWithFilters();
                });
                filterTagsDiv.appendChild(tag);
            }
        });
    }

    highlightText(text, queryWords) {
        if (!queryWords || queryWords.length === 0) return this.escapeHtml(text);
        let highlighted = this.escapeHtml(text);
        queryWords.forEach(word => {
            highlighted = highlighted.replace(new RegExp(`(${word})`, 'gi'), '<span class="highlight">$1</span>');
        });
        return highlighted;
    }

    getContentPreview(content, queryWords, maxLength) {
        if (!content) return '';
        let preview = content;
        if (queryWords && queryWords.length > 0) {
            const sentences = content.split(/[.!?]\s+/);
            const relevant = sentences.find(s => queryWords.some(w => s.toLowerCase().includes(w)));
            if (relevant) {
                const idx = content.indexOf(relevant);
                preview = content.substring(Math.max(0, idx - 50), idx + maxLength);
            } else {
                preview = content.substring(0, maxLength);
            }
        } else {
            preview = content.substring(0, maxLength);
        }
        if (content.length > maxLength) preview += '...';
        return this.highlightText(preview, queryWords);
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
        } catch (e) {
            return dateStr;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getSectionLabel(section) {
        const labels = { 'Menu': 'Menu', 'Store Information': 'Store', 'Brand Information': 'Brand' };
        return labels[section] || section;
    }

    async displayStats() {
        try {
            const params = new URLSearchParams({ q: '*:*', rows: 0, wt: 'json' });
            const response = await fetch(`${this.solrUrl}?${params}`);
            const count = response.ok ? ((await response.json()).response?.numFound || 0) : '?';
            document.getElementById('resultCount').textContent = count;
        } catch (error) {
            console.error('Error getting stats:', error);
            document.getElementById('resultCount').textContent = '?';
        }
    }
    
    async loadAllTags() {
        try {
            const articles = await this.getAllArticles();
            const categories = new Set(), storeTags = new Set(), sections = new Set(), priceRanges = new Set();
            
            articles.forEach(article => {
                if (article.menu_category) categories.add(article.menu_category);
                // Only collect tags from Store Information and Brand Information sections
                if (article.tags?.length && 
                    (article.section === 'Store Information' || article.section === 'Brand Information')) {
                    article.tags.forEach(tag => {
                        // Filter out "others" tag
                        if (tag.toLowerCase() !== 'others') {
                            storeTags.add(tag);
                        }
                    });
                }
                // Also collect ippudo tag from Menu section
                if (article.tags?.length && article.section === 'Menu' && article.tags.includes('ippudo')) {
                    storeTags.add('ippudo');
                }
                // Also collect kagetsu tag from Menu section
                if (article.tags?.length && article.section === 'Menu' && article.tags.includes('kagetsu')) {
                    storeTags.add('kagetsu');
                }
                if (article.section) sections.add(article.section);
                if (article.price_range) priceRanges.add(article.price_range);
            });
            
            // Manually add ippudo tag to store tags (ensure it's always present)
            storeTags.add('ippudo');
            // Manually add kagetsu tag to store tags (ensure it's always present)
            storeTags.add('kagetsu');
            
            // Debug: log store tags
            const sortedStoreTags = Array.from(storeTags).sort();
            console.log('Store tags collected:', sortedStoreTags);
            console.log('storeTagList container exists:', document.getElementById('storeTagList') !== null);
            
            this.displayTagGroup('categoryTagList', Array.from(categories).sort(), 'category', 'category-badge');
            this.displayTagGroup('storeTagList', sortedStoreTags, 'tag', 'tag-badge');
            
            const sectionLabels = { 'Menu': 'Menu', 'Store Information': 'Store', 'Brand Information': 'Brand' };
            const sectionArray = Array.from(sections).map(s => ({
                value: s,
                label: sectionLabels[s] || s
            })).sort((a, b) => a.label.localeCompare(b.label));
            this.displayTagGroup('sectionTagList', sectionArray, 'section', 'tag-badge', true);
            
            // Sort price ranges in logical order
            const priceRangeOrder = ['< ¥1,000', '¥1,000 - ¥2,000', '¥2,000 - ¥3,000', '¥3,000 - ¥5,000', '¥5,000 - ¥10,000', '> ¥10,000'];
            const sortedPriceRanges = Array.from(priceRanges).sort((a, b) => {
                const indexA = priceRangeOrder.indexOf(a);
                const indexB = priceRangeOrder.indexOf(b);
                if (indexA === -1 && indexB === -1) return a.localeCompare(b);
                if (indexA === -1) return 1;
                if (indexB === -1) return -1;
                return indexA - indexB;
            });
            this.displayTagGroup('priceTagList', sortedPriceRanges, 'priceRange', 'tag-badge');
        } catch (error) {
            console.error('Error loading tags:', error);
        }
    }
    
    async getAllArticles() {
        try {
            const params = new URLSearchParams({ q: '*:*', rows: 1000, wt: 'json' });
            const response = await fetch(`${this.solrUrl}?${params}`);
            if (!response.ok) return [];
            const data = await response.json();
            if (data.response?.docs) {
                return data.response.docs.map(doc => ({
                    menu_category: this.getFieldValue(doc.menu_category),
                    tags: this.getFieldArray(doc.tags),
                    section: this.getFieldValue(doc.section),
                    price_range: this.getFieldValue(doc.price_range)
                }));
            }
            return [];
        } catch (error) {
            console.error('Error getting articles:', error);
            return [];
        }
    }
    
    displayTagGroup(containerId, items, filterType, badgeClass, isObject = false) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';
        
        items.forEach(item => {
            const value = isObject ? item.value : item;
            const label = isObject ? item.label : item;
            const isActive = this.activeFilters[filterType] === value;
            
            const tag = document.createElement('span');
            tag.className = `${badgeClass} clickable-tag ${isActive ? 'active' : ''}`;
            tag.dataset.filterType = filterType;
            tag.dataset.filterValue = value;
            tag.textContent = filterType === 'tag' ? `#${label}` : label;
            tag.title = `Click to filter ${label}`;
            
            if (filterType === 'category' && typeof item === 'string') {
                tag.className += ` category-${item.toLowerCase().replace(' ', '-')}`;
            }
            
            tag.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleTagClick(filterType, value);
            });
            
            container.appendChild(tag);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => new ArticleSearch());

