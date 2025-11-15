// Detail page script
class ArticleDetail {
    constructor() {
        this.articleId = null;
        this.article = null;
        this.init();
    }

    init() {
        // Get article ID from URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        this.articleId = urlParams.get('id');
        
        if (!this.articleId) {
            this.showError('No article ID provided');
            return;
        }
        
        this.loadArticle();
    }

    async loadArticle() {
        try {
            // Query Solr to get article details by ID
            // Try Solr proxy first, fallback to direct Solr connection
            const solrProxyUrl = 'http://localhost:8888/solr/RamenProject/select';
            const solrDirectUrl = 'http://localhost:8983/solr/RamenProject/select';
            
            const params = new URLSearchParams({
                q: `id:"${this.articleId}"`,
                wt: 'json',
                fl: '*,score'
            });
            
            let response;
            let data;
            
            // Try proxy first
            try {
                response = await fetch(`${solrProxyUrl}?${params}`);
                if (!response.ok) throw new Error('Proxy failed');
                data = await response.json();
            } catch (proxyError) {
                // Fallback to direct Solr
                console.warn('Solr proxy failed, trying direct connection:', proxyError);
                response = await fetch(`${solrDirectUrl}?${params}`);
                if (!response.ok) throw new Error('Direct connection failed');
                data = await response.json();
            }
            
            if (data.response && data.response.docs && data.response.docs.length > 0) {
                this.article = this.parseDoc(data.response.docs[0]);
                this.displayArticle();
            } else {
                this.showError('Article not found');
            }
        } catch (error) {
            console.error('Error loading article:', error);
            this.showError(`Error loading article details: ${error.message}`);
        }
    }

    parseDoc(doc) {
        return {
            id: doc.id || '',
            url: this.getFieldValue(doc.url),
            title: this.getFieldValue(doc.title),
            content: this.getFieldValue(doc.content),
            section: this.getFieldValue(doc.section),
            menu_item: this.getFieldValue(doc.menu_item),
            menu_category: this.getFieldValue(doc.menu_category),
            ingredients: this.getFieldValue(doc.ingredients),
            store_name: this.getFieldValue(doc.store_name),
            date: this.getFieldValue(doc.date),
            price: this.getFieldValue(doc.price),
            price_range: this.getFieldValue(doc.price_range),
            tags: this.getFieldArray(doc.tags)
        };
    }

    getFieldValue(field, defaultValue = '') {
        if (!field) return defaultValue;
        return Array.isArray(field) ? (field.length > 0 ? String(field[0]) : defaultValue) : String(field);
    }

    getFieldArray(field, defaultValue = []) {
        if (!field) return defaultValue;
        return Array.isArray(field) ? field.map(String) : [String(field)];
    }

    displayArticle() {
        const loading = document.getElementById('loading');
        const error = document.getElementById('error');
        const detailContent = document.getElementById('detailContent');
        
        loading.style.display = 'none';
        error.style.display = 'none';
        detailContent.style.display = 'block';
        
        // Set title
        document.getElementById('detailTitle').textContent = this.article.title;
        
        // Set price
        const priceDiv = document.getElementById('detailPrice');
        if (this.article.price) {
            priceDiv.innerHTML = `<span class="product-price" style="font-size: 1.3em; font-weight: bold; color: #4CAF50;">${this.escapeHtml(this.article.price)}</span>`;
        } else {
            priceDiv.style.display = 'none';
        }
        
        // Set meta information
        const metaDiv = document.getElementById('detailMeta');
        const metaItems = [];
        
        if (this.article.menu_item && this.article.menu_item !== this.article.title) {
            metaItems.push(`<div class="detail-meta-item">🍜 <strong>Menu Item:</strong> ${this.escapeHtml(this.article.menu_item)}</div>`);
        }
        
        if (this.article.menu_category) {
            metaItems.push(`<div class="detail-meta-item">📂 <strong>Category:</strong> ${this.escapeHtml(this.article.menu_category)}</div>`);
        }
        
        if (this.article.section) {
            metaItems.push(`<div class="detail-meta-item">📋 <strong>Type:</strong> ${this.escapeHtml(this.article.section)}</div>`);
        }
        
        if (this.article.store_name) {
            metaItems.push(`<div class="detail-meta-item">📍 <strong>Store:</strong> ${this.escapeHtml(this.article.store_name)}</div>`);
        }
        
        if (this.article.date) {
            metaItems.push(`<div class="detail-meta-item">📅 <strong>Date:</strong> ${this.escapeHtml(this.article.date)}</div>`);
        }
        
        metaDiv.innerHTML = metaItems.join('');
        
        // Set sections
        const sectionsDiv = document.getElementById('detailSections');
        const sections = [];
        
        if (this.article.ingredients) {
            sections.push(`
                <div class="detail-section">
                    <div class="detail-section-title">Ingredients</div>
                    <div class="detail-content">${this.escapeHtml(this.article.ingredients)}</div>
                </div>
            `);
        }
        
        sectionsDiv.innerHTML = sections.join('');
        
        // Set content
        document.getElementById('detailContentText').textContent = this.article.content;
        
        // Set tags
        if (this.article.tags && this.article.tags.length > 0) {
            const tagsDiv = document.getElementById('detailTags');
            const tagsList = document.getElementById('detailTagsList');
            tagsDiv.style.display = 'block';
            tagsList.innerHTML = this.article.tags.map(tag => 
                `<span class="tag-badge">#${this.escapeHtml(tag)}</span>`
            ).join('');
        }
        
        // Set external link
        if (this.article.url) {
            const externalLink = document.getElementById('externalLink');
            externalLink.href = this.article.url;
            externalLink.style.display = 'inline-block';
        }
    }

    showError(message) {
        const loading = document.getElementById('loading');
        const error = document.getElementById('error');
        const detailContent = document.getElementById('detailContent');
        
        loading.style.display = 'none';
        detailContent.style.display = 'none';
        error.style.display = 'block';
        error.querySelector('p').textContent = message;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new ArticleDetail();
});

