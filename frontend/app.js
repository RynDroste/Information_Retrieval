class ArticleSearch {
    constructor() {
        this.filteredArticles = [];
        this.activeFilters = { section: null, category: null, tag: null };
        this.solrUrl = 'http://localhost:8888/solr/RamenProject/select';
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.displayStats();
        await this.loadAllTags();
        this.updateActiveFiltersDisplay();
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
            url: this.getFieldValue(doc.url),
            title: this.getFieldValue(doc.title),
            content: this.getFieldValue(doc.content),
            section: this.getFieldValue(doc.section),
            menu_item: this.getFieldValue(doc.menu_item),
            menu_category: this.getFieldValue(doc.menu_category),
            ingredients: this.getFieldValue(doc.ingredients),
            store_name: this.getFieldValue(doc.store_name),
            date: this.getFieldValue(doc.date),
            tags: this.getFieldArray(doc.tags)
        }));
    }

    async searchSolr(query) {
        const queryLower = query.toLowerCase().trim();
        let bq = '';
        
        if (queryLower === 'afuri' || queryLower.includes('afuri')) {
            bq = 'section:"Brand Information"^7.0 section:"Store Information"^6.5';
        } else {
            const categoryBoosts = {
                'store': 'section:"Store Information"^5.0',
                'drink': 'menu_category:"Drinks"^5.0',
                'drinks': 'menu_category:"Drinks"^5.0',
                'ramen': 'menu_category:"Ramen"^5.0',
                'noodle': 'menu_category:"Noodles"^5.0',
                'noodles': 'menu_category:"Noodles"^5.0',
                'side': 'menu_category:"Side Dishes"^5.0',
                'side dish': 'menu_category:"Side Dishes"^5.0',
                'side dishes': 'menu_category:"Side Dishes"^5.0',
                'tsukemen': 'menu_category:"Tsukemen"^5.0',
                'chi-yu': 'menu_category:"Chi-yu"^5.0',
                'chiyu': 'menu_category:"Chi-yu"^5.0'
            };
            
            for (const [keyword, boost] of Object.entries(categoryBoosts)) {
                if (queryLower === keyword || queryLower.includes(keyword)) {
                    bq = boost;
                    break;
                }
            }
        }
        
        const params = new URLSearchParams({
            q: query,
            defType: 'edismax',
            qf: 'title^2.0 content^1.5 menu_item^2.5 ingredients^1.0 menu_category^2.0 store_name^3.0',
            pf: 'title^3.0 menu_item^3.0 store_name^4.0',
            rows: 1000,
            wt: 'json'
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

            if (data.response?.docs) {
                this.filteredArticles = this.parseDocs(data.response.docs);
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
        return tags.map(tag => {
            const isActive = this.activeFilters[filterType] === tag;
            return `<span class="tag-badge clickable-tag ${isActive ? 'active' : ''}" 
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
            const { section, menuCategory, tags, ingredients } = {
                section: article.section || '',
                menuCategory: article.menu_category || '',
                tags: article.tags || [],
                ingredients: article.ingredients || ''
            };

            let categoryLine = '', tagsLine = '', ingredientsLine = '';
            
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
                if (ingredients) ingredientsLine = `<div class="ingredients-line"><span class="section-label">Ingredients:</span><span class="ingredients-text">${this.escapeHtml(ingredients)}</span></div>`;
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

            return `<div class="article-card">
                <h2><a href="${article.url}" target="_blank">${this.highlightText(article.title, queryWords)}</a></h2>
                ${categoryLine}${tagsLine}${ingredientsLine}
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
        this.activeFilters = { section: null, category: null, tag: null };
        this.updateActiveFiltersDisplay();
        this.performSearchWithFilters();
    }
    
    updateActiveFiltersDisplay() {
        const activeFiltersDiv = document.getElementById('activeFilters');
        const filterTagsDiv = document.getElementById('filterTags');
        const hasFilters = this.activeFilters.section || this.activeFilters.category || this.activeFilters.tag;
        
        if (!hasFilters) {
            activeFiltersDiv.style.display = 'none';
            return;
        }

        activeFiltersDiv.style.display = 'flex';
        filterTagsDiv.innerHTML = '';
        
        ['section', 'category', 'tag'].forEach(type => {
            if (this.activeFilters[type]) {
                const tag = document.createElement('span');
                tag.className = 'filter-tag';
                tag.textContent = type === 'tag' ? `#${this.activeFilters[type]}` : 
                    (type === 'section' ? this.getSectionLabel(this.activeFilters[type]) : this.activeFilters[type]);
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
            const categories = new Set(), storeTags = new Set(), sections = new Set();
            
            articles.forEach(article => {
                if (article.menu_category) categories.add(article.menu_category);
                if (article.tags?.length) article.tags.forEach(tag => storeTags.add(tag));
                if (article.section) sections.add(article.section);
            });
            
            this.displayTagGroup('categoryTagList', Array.from(categories).sort(), 'category', 'category-badge');
            this.displayTagGroup('storeTagList', Array.from(storeTags).sort(), 'tag', 'tag-badge');
            
            const sectionLabels = { 'Menu': 'Menu', 'Store Information': 'Store', 'Brand Information': 'Brand' };
            const sectionArray = Array.from(sections).map(s => ({
                value: s,
                label: sectionLabels[s] || s
            })).sort((a, b) => a.label.localeCompare(b.label));
            this.displayTagGroup('sectionTagList', sectionArray, 'section', 'tag-badge', true);
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
                    section: this.getFieldValue(doc.section)
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
