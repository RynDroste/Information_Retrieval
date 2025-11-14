// Article Search Application
class ArticleSearch {
    constructor() {
        this.filteredArticles = [];
        this.activeFilters = {
            section: null,
            category: null,
            tag: null
        };
        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.displayStats();
        this.updateActiveFiltersDisplay();
    }

    setupEventListeners() {
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        const sortBy = document.getElementById('sortBy');

        // Search on button click
        searchBtn.addEventListener('click', () => this.performSearch());

        // Search on Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Real-time search (optional - can be enabled)
        // searchInput.addEventListener('input', () => this.performSearch());

        // Sort change
        sortBy.addEventListener('change', () => {
            if (this.filteredArticles.length > 0) {
                this.sortArticles();
                this.displayResults();
            }
        });

        // Clear filters button
        const clearFiltersBtn = document.getElementById('clearFilters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }
    }

    async performSearch() {
        // Clear filters when performing manual search
        // Or keep filters - let's keep them for now
        const query = document.getElementById('searchInput').value.trim();
        
        // Build query with active filters
        let queryParts = [];
        
        if (this.activeFilters.section) {
            queryParts.push(`section:"${this.activeFilters.section}"`);
        }
        
        if (this.activeFilters.category) {
            queryParts.push(`menu_category:"${this.activeFilters.category}"`);
        }
        
        if (this.activeFilters.tag) {
            queryParts.push(`tags:"${this.activeFilters.tag}"`);
        }
        
        let finalQuery = '*:*';
        
        if (queryParts.length > 0) {
            finalQuery = queryParts.join(' AND ');
            if (query) {
                finalQuery = `(${finalQuery}) AND (${query})`;
            }
        } else if (query) {
            finalQuery = query;
        }

        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const noResults = document.getElementById('noResults');

        loading.style.display = 'block';
        results.innerHTML = '';
        noResults.style.display = 'none';

        try {
            await this.searchSolr(finalQuery);
        } catch (error) {
            console.error('Search error:', error);
            let errorMessage = 'Error performing search. ';
            if (error.message.includes('fetch') || error.message.includes('Failed to fetch')) {
                errorMessage += 'Cannot connect to Solr server. Please make sure Solr is running on http://localhost:8983';
            } else if (error.message.includes('CORS')) {
                errorMessage += 'CORS error. Please check Solr CORS configuration.';
            } else {
                errorMessage += error.message || 'Please check the browser console for details.';
            }
            results.innerHTML = `<div class="no-results"><p>${errorMessage}</p><p style="font-size: 12px; color: #6c757d; margin-top: 10px;">If Solr is running, check browser console (F12) for more details.</p></div>`;
        } finally {
            loading.style.display = 'none';
        }
    }

    async searchSolr(query) {
        // Use proxy to avoid CORS issues
        const solrUrl = 'http://localhost:8888/solr/afuri_menu/select';
        const params = new URLSearchParams({
            q: query,
            rows: 1000,
            wt: 'json'
        });

        try {
            const response = await fetch(`${solrUrl}?${params}`);
            
            if (!response.ok) {
                throw new Error(`Solr request failed: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();

            if (data.response && data.response.docs) {
                // Helper function to safely extract field value (Solr may return arrays)
                const getFieldValue = (field, defaultValue = '') => {
                    if (!field) return defaultValue;
                    if (Array.isArray(field)) {
                        return field.length > 0 ? String(field[0]) : defaultValue;
                    }
                    return String(field);
                };
                
                const getFieldArray = (field, defaultValue = []) => {
                    if (!field) return defaultValue;
                    if (Array.isArray(field)) {
                        return field.map(String);
                    }
                    return [String(field)];
                };
                
                this.filteredArticles = data.response.docs.map(doc => ({
                    url: getFieldValue(doc.url),
                    title: getFieldValue(doc.title),
                    content: getFieldValue(doc.content),
                    section: getFieldValue(doc.section),
                    menu_item: getFieldValue(doc.menu_item),
                    menu_category: getFieldValue(doc.menu_category),
                    ingredients: getFieldValue(doc.ingredients),
                    store_name: getFieldValue(doc.store_name),
                    date: getFieldValue(doc.date),
                    tags: getFieldArray(doc.tags)
                }));

                this.sortArticles();
                this.displayResults();
                this.updateActiveFiltersDisplay();
            } else {
                this.filteredArticles = [];
                this.displayResults();
                this.updateActiveFiltersDisplay();
            }
        } catch (error) {
            console.error('Solr search error details:', error);
            // Check for specific error types
            if (error.message.includes('fetch') || error.message.includes('Failed to fetch') || error.name === 'TypeError') {
                // This is likely a CORS or connection error
                const errorMsg = error.message || error.toString();
                if (errorMsg.includes('CORS') || errorMsg.includes('cross-origin')) {
                    throw new Error('CORS error: Browser blocked the request. Solr may need CORS configuration.');
                } else {
                    throw new Error('Cannot connect to Solr server. Please make sure Solr is running on http://localhost:8983. Error: ' + errorMsg);
                }
            }
            throw error;
        }
    }

    sortArticles() {
        const sortBy = document.getElementById('sortBy').value;

        switch (sortBy) {
            case 'title-asc':
                this.filteredArticles.sort((a, b) => {
                    const titleA = (a.title || '').toLowerCase();
                    const titleB = (b.title || '').toLowerCase();
                    return titleA.localeCompare(titleB);
                });
                break;
            case 'category':
                this.filteredArticles.sort((a, b) => {
                    const catA = (a.menu_category || '').toLowerCase();
                    const catB = (b.menu_category || '').toLowerCase();
                    if (catA !== catB) {
                        return catA.localeCompare(catB);
                    }
                    // If same category, sort by title
                    const titleA = (a.title || '').toLowerCase();
                    const titleB = (b.title || '').toLowerCase();
                    return titleA.localeCompare(titleB);
                });
                break;
            // 'relevance' is already sorted by Solr
        }
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
            const highlightedTitle = this.highlightText(article.title, queryWords);
            const contentPreview = this.getContentPreview(article.content, queryWords, 300);
            const date = article.date ? this.formatDate(article.date) : '';
            const menuItem = article.menu_item || '';
            const menuCategory = article.menu_category || '';
            const storeName = article.store_name || '';
            const tags = article.tags || [];
            const section = article.section || '';
            const ingredients = article.ingredients || '';

            // For menu items: first line shows "菜单: Ramen", second line shows "店铺: #afuri", third line shows ingredients
            // For stores: only show "店铺: #afuri"
            let categoryLine = '';
            let tagsLine = '';
            let ingredientsLine = '';
            
            if (section === 'Menu' && menuCategory) {
                // Menu items: first line shows "菜单" and "Ramen" as tags
                const isSectionActive = this.activeFilters.section === 'Menu';
                const isCategoryActive = this.activeFilters.category === menuCategory;
                categoryLine = `<div class="category-line">
                    <span class="tag-badge tag-menu clickable-tag ${isSectionActive ? 'active' : ''}" 
                          data-filter-type="section" data-filter-value="Menu" 
                          title="点击筛选菜单项">菜单</span>
                    <span class="category-badge category-${menuCategory.toLowerCase().replace(' ', '-')} clickable-tag ${isCategoryActive ? 'active' : ''}" 
                          data-filter-type="category" data-filter-value="${this.escapeHtml(menuCategory)}" 
                          title="点击筛选 ${this.escapeHtml(menuCategory)} 分类">${this.escapeHtml(menuCategory)}</span>
                </div>`;
                
                // Second line shows "店铺" and "#afuri" as tags
                tagsLine = tags.length > 0 ? `
                    <div class="tags-line">
                        <span class="tag-badge tag-store clickable-tag ${this.activeFilters.section === 'Store Information' ? 'active' : ''}" 
                              data-filter-type="section" data-filter-value="Store Information" 
                              title="点击筛选店铺信息">店铺</span>
                        ${tags.map(tag => {
                            const isTagActive = this.activeFilters.tag === tag;
                            return `<span class="tag-badge clickable-tag ${isTagActive ? 'active' : ''}" 
                                    data-filter-type="tag" data-filter-value="${this.escapeHtml(tag)}" 
                                    title="点击筛选 #${this.escapeHtml(tag)}">#${this.escapeHtml(tag)}</span>`;
                        }).join('')}
                    </div>
                ` : '';
                
                // Third line shows ingredients
                ingredientsLine = ingredients ? `
                    <div class="ingredients-line">
                        <span class="section-label">原材料:</span>
                        <span class="ingredients-text">${this.escapeHtml(ingredients)}</span>
                    </div>
                ` : '';
            } else if (section === 'Store Information') {
                // Stores: show "店铺" and "#afuri" as tags
                const isSectionActive = this.activeFilters.section === 'Store Information';
                tagsLine = tags.length > 0 ? `
                    <div class="tags-line">
                        <span class="tag-badge tag-store clickable-tag ${isSectionActive ? 'active' : ''}" 
                              data-filter-type="section" data-filter-value="Store Information" 
                              title="点击筛选店铺信息">店铺</span>
                        ${tags.map(tag => {
                            const isTagActive = this.activeFilters.tag === tag;
                            return `<span class="tag-badge clickable-tag ${isTagActive ? 'active' : ''}" 
                                    data-filter-type="tag" data-filter-value="${this.escapeHtml(tag)}" 
                                    title="点击筛选 #${this.escapeHtml(tag)}">#${this.escapeHtml(tag)}</span>`;
                        }).join('')}
                    </div>
                ` : '';
            } else if (section === 'Brand Information') {
                // Brand: show "品牌" and "#afuri" as tags
                const isSectionActive = this.activeFilters.section === 'Brand Information';
                tagsLine = tags.length > 0 ? `
                    <div class="tags-line">
                        <span class="tag-badge tag-brand clickable-tag ${isSectionActive ? 'active' : ''}" 
                              data-filter-type="section" data-filter-value="Brand Information" 
                              title="点击筛选品牌信息">品牌</span>
                        ${tags.map(tag => {
                            const isTagActive = this.activeFilters.tag === tag;
                            return `<span class="tag-badge clickable-tag ${isTagActive ? 'active' : ''}" 
                                    data-filter-type="tag" data-filter-value="${this.escapeHtml(tag)}" 
                                    title="点击筛选 #${this.escapeHtml(tag)}">#${this.escapeHtml(tag)}</span>`;
                        }).join('')}
                    </div>
                ` : '';
            }

            return `
                <div class="article-card">
                    <h2><a href="${article.url}" target="_blank">${highlightedTitle}</a></h2>
                    ${categoryLine}
                    ${tagsLine}
                    ${ingredientsLine}
                    <div class="article-meta">
                        ${menuItem && menuItem !== article.title ? `<span>🍜 ${menuItem}</span>` : ''}
                        ${storeName ? `<span>📍 ${storeName}</span>` : ''}
                        ${date ? `<span>📅 ${date}</span>` : ''}
                    </div>
                    <div class="article-content">${contentPreview}</div>
                </div>
            `;
        }).join('');
        
        // Add click event listeners to tags after rendering
        this.attachTagClickListeners();
    }
    
    attachTagClickListeners() {
        // Add click listeners to all clickable tags
        document.querySelectorAll('.clickable-tag').forEach(tag => {
            tag.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const filterType = tag.getAttribute('data-filter-type');
                const filterValue = tag.getAttribute('data-filter-value');
                this.handleTagClick(filterType, filterValue);
            });
        });
    }
    
    handleTagClick(filterType, filterValue) {
        // Toggle filter: if same filter is clicked, remove it; otherwise, set it
        if (this.activeFilters[filterType] === filterValue) {
            // Remove filter
            this.activeFilters[filterType] = null;
        } else {
            // Set filter (clear other filters of the same type)
            this.activeFilters[filterType] = filterValue;
        }
        
        // Update display
        this.updateActiveFiltersDisplay();
        
        // Perform search with active filters
        this.performSearchWithFilters();
    }
    
    clearAllFilters() {
        this.activeFilters = {
            section: null,
            category: null,
            tag: null
        };
        this.updateActiveFiltersDisplay();
        // Perform search to show all results
        this.performSearchWithFilters();
    }
    
    updateActiveFiltersDisplay() {
        const activeFiltersDiv = document.getElementById('activeFilters');
        const filterTagsDiv = document.getElementById('filterTags');
        
        const hasFilters = this.activeFilters.section || 
                         this.activeFilters.category || 
                         this.activeFilters.tag;
        
        if (!hasFilters) {
            activeFiltersDiv.style.display = 'none';
            return;
        }
        
        activeFiltersDiv.style.display = 'flex';
        filterTagsDiv.innerHTML = '';
        
        if (this.activeFilters.section) {
            const filterTag = document.createElement('span');
            filterTag.className = 'filter-tag';
            filterTag.textContent = this.getSectionLabel(this.activeFilters.section);
            filterTag.addEventListener('click', () => {
                this.activeFilters.section = null;
                this.updateActiveFiltersDisplay();
                this.performSearchWithFilters();
            });
            filterTagsDiv.appendChild(filterTag);
        }
        
        if (this.activeFilters.category) {
            const filterTag = document.createElement('span');
            filterTag.className = 'filter-tag';
            filterTag.textContent = this.activeFilters.category;
            filterTag.addEventListener('click', () => {
                this.activeFilters.category = null;
                this.updateActiveFiltersDisplay();
                this.performSearchWithFilters();
            });
            filterTagsDiv.appendChild(filterTag);
        }
        
        if (this.activeFilters.tag) {
            const filterTag = document.createElement('span');
            filterTag.className = 'filter-tag';
            filterTag.textContent = `#${this.activeFilters.tag}`;
            filterTag.addEventListener('click', () => {
                this.activeFilters.tag = null;
                this.updateActiveFiltersDisplay();
                this.performSearchWithFilters();
            });
            filterTagsDiv.appendChild(filterTag);
        }
    }
    
    async performSearchWithFilters() {
        // Build Solr query based on active filters
        let queryParts = [];
        
        if (this.activeFilters.section) {
            queryParts.push(`section:"${this.activeFilters.section}"`);
        }
        
        if (this.activeFilters.category) {
            queryParts.push(`menu_category:"${this.activeFilters.category}"`);
        }
        
        if (this.activeFilters.tag) {
            queryParts.push(`tags:"${this.activeFilters.tag}"`);
        }
        
        // If no filters and no search query, show all
        const searchInput = document.getElementById('searchInput').value.trim();
        let finalQuery = '*:*';
        
        if (queryParts.length > 0) {
            finalQuery = queryParts.join(' AND ');
            // If there's also a search query, combine them
            if (searchInput) {
                finalQuery = `(${finalQuery}) AND (${searchInput})`;
            }
        } else if (searchInput) {
            finalQuery = searchInput;
        }
        
        // Update search input to show active filters (optional)
        // Perform search
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const noResults = document.getElementById('noResults');
        
        loading.style.display = 'block';
        results.innerHTML = '';
        noResults.style.display = 'none';
        
        try {
            await this.searchSolr(finalQuery);
        } catch (error) {
            console.error('Search error:', error);
            let errorMessage = 'Error performing search. ';
            if (error.message.includes('fetch') || error.message.includes('Failed to fetch')) {
                errorMessage += 'Cannot connect to Solr server. Please make sure Solr is running on http://localhost:8983';
            } else if (error.message.includes('CORS')) {
                errorMessage += 'CORS error. Please check Solr CORS configuration.';
            } else {
                errorMessage += error.message || 'Please check the browser console for details.';
            }
            results.innerHTML = `<div class="no-results"><p>${errorMessage}</p><p style="font-size: 12px; color: #6c757d; margin-top: 10px;">If Solr is running, check browser console (F12) for more details.</p></div>`;
        } finally {
            loading.style.display = 'none';
        }
    }

    highlightText(text, queryWords) {
        if (!queryWords || queryWords.length === 0) {
            return this.escapeHtml(text);
        }

        let highlighted = this.escapeHtml(text);
        queryWords.forEach(word => {
            const regex = new RegExp(`(${word})`, 'gi');
            highlighted = highlighted.replace(regex, '<span class="highlight">$1</span>');
        });

        return highlighted;
    }

    getContentPreview(content, queryWords, maxLength) {
        if (!content) return '';

        const contentLower = content.toLowerCase();
        let preview = content;

        // Try to find a sentence containing query words
        if (queryWords && queryWords.length > 0) {
            const sentences = content.split(/[.!?]\s+/);
            const relevantSentence = sentences.find(sentence => 
                queryWords.some(word => sentence.toLowerCase().includes(word))
            );

            if (relevantSentence) {
                const index = content.indexOf(relevantSentence);
                const start = Math.max(0, index - 50);
                preview = content.substring(start, start + maxLength);
            } else {
                preview = content.substring(0, maxLength);
            }
        } else {
            preview = content.substring(0, maxLength);
        }

        if (content.length > maxLength) {
            preview += '...';
        }

        return this.highlightText(preview, queryWords);
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
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
        const sectionLabels = {
            'Menu': '菜单',
            'Store Information': '店铺',
            'Brand Information': '品牌'
        };
        return sectionLabels[section] || section;
    }

    async displayStats() {
        try {
            // Use proxy to avoid CORS issues
            const solrUrl = 'http://localhost:8888/solr/afuri_menu/select';
            const params = new URLSearchParams({
                q: '*:*',
                rows: 0,
                wt: 'json'
            });

            const response = await fetch(`${solrUrl}?${params}`);
            if (response.ok) {
                const data = await response.json();
                const count = data.response?.numFound || 0;
                document.getElementById('resultCount').textContent = count;
            } else {
                document.getElementById('resultCount').textContent = '?';
            }
        } catch (error) {
            console.error('Error getting stats from Solr:', error);
            document.getElementById('resultCount').textContent = '?';
        }
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new ArticleSearch();
});

