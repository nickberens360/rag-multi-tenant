import BasePage from './BasePage.js';

class FollowupSettingsPage extends BasePage {
  constructor(page) {
    super(page);
    
    // Metrics cards
    this.activeCategoriesCard = page.locator('[data-testid="active-categories"], .metric-card').first();
    this.totalQuestionsCard = page.locator('[data-testid="total-questions"], .metric-card').nth(1);
    this.inactiveCategoriesCard = page.locator('[data-testid="inactive-categories"], .metric-card').nth(2);
    this.serviceModeCard = page.locator('[data-testid="service-mode"], .metric-card').nth(3);
    
    // System settings
    this.serviceToggle = page.locator('.v-switch input, [data-testid="service-toggle"]');
    this.serviceTypeSelect = page.locator('.v-select [role="combobox"], [data-testid="service-type"]');
    this.questionLimitSlider = page.locator('.v-slider input, [data-testid="question-limit"]');
    
    // Category management
    this.addCategoryButton = page.locator('button:has-text("Add Category"), [data-testid="add-category"]');
    this.categoriesList = page.locator('.categories-card, [data-testid="categories-list"]');
    this.categoryAccordion = page.locator('.v-expansion-panels, [data-testid="category-accordion"]');
    
    // Bulk actions
    this.bulkActionsCard = page.locator('.bulk-actions-card, [data-testid="bulk-actions"]');
    this.bulkActivateButton = page.locator('button:has-text("Activate"), [data-testid="bulk-activate"]');
    this.bulkDeactivateButton = page.locator('button:has-text("Deactivate"), [data-testid="bulk-deactivate"]');
    this.bulkDeleteButton = page.locator('button:has-text("Delete"), [data-testid="bulk-delete"]');
    
    // Empty state
    this.emptyState = page.locator('.empty-state, [data-testid="empty-state"]');
    this.createFirstCategoryButton = page.locator('button:has-text("Create First Category")');
    
    // Dialogs
    this.categoryDialog = page.locator('.v-dialog:visible');
    this.deleteConfirmDialog = page.locator('.v-dialog:visible:has-text("Delete")');
  }

  async goto() {
    await this.navigateTo('/settings/followup');
    await this.waitForPageLoad();
  }

  async waitForPageLoad() {
    await this.waitForLoading();
    // Wait for metrics cards to load
    await this.activeCategoriesCard.waitFor({ timeout: 10000 });
  }

  // Metrics methods
  async getMetrics() {
    const metrics = {};
    
    try {
      // Extract numeric values from metric cards
      const activeText = await this.activeCategoriesCard.locator('.metric-value').textContent();
      metrics.activeCategories = parseInt(activeText.trim());
      
      const totalText = await this.totalQuestionsCard.locator('.metric-value').textContent();
      metrics.totalQuestions = parseInt(totalText.trim());
      
      const inactiveText = await this.inactiveCategoriesCard.locator('.metric-value').textContent();
      metrics.inactiveCategories = parseInt(inactiveText.trim());
      
      const serviceModeText = await this.serviceModeCard.locator('.metric-value').textContent();
      metrics.serviceMode = serviceModeText.trim();
    } catch (error) {
      console.warn('Could not extract all metrics:', error.message);
    }
    
    return metrics;
  }

  // System settings methods
  async toggleService() {
    await this.serviceToggle.click();
    await this.waitForLoading();
    const toast = await this.waitForToast();
    return toast;
  }

  async setServiceType(type) {
    await this.serviceTypeSelect.click();
    await this.page.locator(`.v-list-item:has-text("${type}")`).click();
    await this.waitForLoading();
  }

  async setQuestionLimit(value) {
    // Use slider to set value
    const slider = this.questionLimitSlider;
    await slider.fill(value.toString());
    await this.waitForLoading();
  }

  async getServiceSettings() {
    const isEnabled = await this.serviceToggle.isChecked();
    
    let serviceType = '';
    try {
      serviceType = await this.serviceTypeSelect.locator('.v-select__selection').textContent();
    } catch {}
    
    let questionLimit = 3; // default
    try {
      questionLimit = parseInt(await this.questionLimitSlider.inputValue());
    } catch {}
    
    return {
      enabled: isEnabled,
      serviceType: serviceType.trim(),
      questionLimit,
    };
  }

  // Category management methods
  async getCategoryCount() {
    const categoryPanels = this.categoryAccordion.locator('.v-expansion-panel');
    return await categoryPanels.count();
  }

  async addCategory() {
    await this.addCategoryButton.click();
    await this.waitForDialog();
  }

  async createFirstCategory() {
    if (await this.createFirstCategoryButton.isVisible()) {
      await this.createFirstCategoryButton.click();
      await this.waitForDialog();
    }
  }

  async openCategory(categoryName) {
    const categoryPanel = this.categoryAccordion.locator(`[data-testid="category-${categoryName}"], :has-text("${categoryName}")`);
    const header = categoryPanel.locator('.v-expansion-panel-title');
    
    if (await header.isVisible()) {
      await header.click();
      await this.waitForLoading();
    }
  }

  async selectCategory(categoryName) {
    const categoryCheckbox = this.categoryAccordion.locator(
      `.v-expansion-panel:has-text("${categoryName}") .v-checkbox input`
    );
    
    if (await categoryCheckbox.isVisible()) {
      await categoryCheckbox.check();
    }
  }

  async getSelectedCategoryCount() {
    const selectedCheckboxes = this.categoryAccordion.locator('.v-checkbox input:checked');
    return await selectedCheckboxes.count();
  }

  // Bulk actions methods
  async performBulkActivate() {
    if (await this.bulkActivateButton.isVisible()) {
      await this.bulkActivateButton.click();
      await this.waitForLoading();
      return await this.waitForToast();
    }
  }

  async performBulkDeactivate() {
    if (await this.bulkDeactivateButton.isVisible()) {
      await this.bulkDeactivateButton.click();
      await this.waitForLoading();
      return await this.waitForToast();
    }
  }

  async performBulkDelete() {
    if (await this.bulkDeleteButton.isVisible()) {
      await this.bulkDeleteButton.click();
      await this.waitForDialog();
      
      // Confirm deletion
      const confirmButton = this.deleteConfirmDialog.locator('button:has-text("Delete")');
      await confirmButton.click();
      await this.waitForLoading();
      return await this.waitForToast();
    }
  }

  // Dialog methods
  async fillCategoryForm(data) {
    const dialog = this.categoryDialog;
    
    if (data.name) {
      await dialog.locator('input[label*="Name"], input[placeholder*="name"]').first().fill(data.name);
    }
    
    if (data.displayName) {
      await dialog.locator('input[label*="Display"], input[placeholder*="display"]').fill(data.displayName);
    }
    
    if (data.description) {
      await dialog.locator('textarea, input[label*="Description"]').fill(data.description);
    }
    
    if (data.icon) {
      await dialog.locator('input[label*="Icon"]').fill(data.icon);
    }
  }

  async saveCategoryForm() {
    const saveButton = this.categoryDialog.locator('button:has-text("Save"), button:has-text("Add"), button:has-text("Create")');
    await saveButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
    await this.waitForLoading();
    return await this.waitForToast();
  }

  async cancelCategoryForm() {
    const cancelButton = this.categoryDialog.locator('button:has-text("Cancel")');
    await cancelButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
  }

  // Question management methods
  async addQuestionToCategory(categoryName) {
    // First open the category
    await this.openCategory(categoryName);
    
    // Find the add question button within that category
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const addQuestionButton = categoryPanel.locator('button:has-text("Add Question")');
    
    await addQuestionButton.click();
    await this.waitForDialog();
  }

  async getQuestionsInCategory(categoryName) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const questions = categoryPanel.locator('.v-list-item');
    
    return await questions.count();
  }

  async editQuestionInCategory(categoryName, questionIndex) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const questions = categoryPanel.locator('.v-list-item');
    const editButton = questions.nth(questionIndex).locator('button:has([class*="edit"])');
    
    await editButton.click();
    await this.waitForDialog();
  }

  async deleteQuestionInCategory(categoryName, questionIndex) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const questions = categoryPanel.locator('.v-list-item');
    const deleteButton = questions.nth(questionIndex).locator('button:has([class*="delete"])');
    
    await deleteButton.click();
    await this.waitForDialog();
  }

  async confirmDeleteQuestion() {
    const confirmButton = this.page.locator('.v-dialog:visible button:has-text("Delete")');
    await confirmButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
    await this.waitForLoading();
    return await this.waitForToast();
  }

  async moveQuestionUp(categoryName, questionIndex) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const questions = categoryPanel.locator('.v-list-item');
    const upButton = questions.nth(questionIndex).locator('button:has([class*="arrow-up"])');
    
    await upButton.click();
    await this.waitForLoading();
  }

  async toggleQuestionActive(categoryName, questionIndex) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const questions = categoryPanel.locator('.v-list-item');
    const toggleButton = questions.nth(questionIndex).locator('button:has([class*="eye"])');
    
    await toggleButton.click();
    await this.waitForLoading();
  }

  async selectQuestionsInCategory(categoryName, questionIndices) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const questions = categoryPanel.locator('.v-list-item');
    
    for (const index of questionIndices) {
      const checkbox = questions.nth(index).locator('.v-checkbox input');
      await checkbox.check();
    }
  }

  async selectAllQuestionsInCategory(categoryName) {
    await this.openCategory(categoryName);
    
    const categoryPanel = this.categoryAccordion.locator(`:has-text("${categoryName}")`);
    const checkboxes = categoryPanel.locator('.v-list-item .v-checkbox input');
    const count = await checkboxes.count();
    
    for (let i = 0; i < count; i++) {
      await checkboxes.nth(i).check();
    }
  }

  async performBulkQuestionDeactivate() {
    const bulkDeactivateButton = this.page.locator('button:has-text("Deactivate Questions"), [data-testid="bulk-deactivate-questions"]');
    if (await bulkDeactivateButton.isVisible()) {
      await bulkDeactivateButton.click();
      await this.waitForLoading();
      return await this.waitForToast();
    }
  }

  async fillQuestionForm(data) {
    const dialog = this.page.locator('.v-dialog:visible');
    
    if (data.questionText) {
      await dialog.locator('textarea, input[label*="Question"]').fill(data.questionText);
    }
    
    if (data.sortOrder !== undefined) {
      await dialog.locator('input[type="number"], input[label*="Order"]').fill(data.sortOrder.toString());
    }
  }

  async saveQuestionForm() {
    const saveButton = this.page.locator('.v-dialog:visible button:has-text("Save"), .v-dialog:visible button:has-text("Add")');
    await saveButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
    await this.waitForLoading();
    return await this.waitForToast();
  }

  async cancelQuestionForm() {
    const cancelButton = this.page.locator('.v-dialog:visible button:has-text("Cancel")');
    await cancelButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
  }

  async hasQuestionValidationErrors() {
    const errorElements = this.page.locator('.v-dialog:visible .v-messages__message, .v-dialog:visible .error--text');
    return (await errorElements.count()) > 0;
  }

  async getQuestionFormText() {
    const textField = this.page.locator('.v-dialog:visible textarea, .v-dialog:visible input[label*="Question"]');
    return await textField.inputValue();
  }

  async searchQuestions(query) {
    const searchInput = this.page.locator('input[placeholder*="Search"], [data-testid="search-questions"]');
    if (await searchInput.isVisible()) {
      await searchInput.fill(query);
      await this.page.keyboard.press('Enter');
      await this.waitForLoading();
    }
  }

  async getSearchResults() {
    const results = this.page.locator('.search-results .v-list-item, .question-search-result');
    const count = await results.count();
    const texts = [];
    
    for (let i = 0; i < count; i++) {
      texts.push(await results.nth(i).textContent());
    }
    
    return texts;
  }

  async hasPagination() {
    return await this.page.locator('.v-pagination, .pagination').isVisible();
  }

  async goToNextPage() {
    const nextButton = this.page.locator('.v-pagination button:has-text("Next"), .pagination .next');
    if (await nextButton.isVisible() && await nextButton.isEnabled()) {
      await nextButton.click();
      await this.waitForLoading();
    }
  }

  async goToPreviousPage() {
    const prevButton = this.page.locator('.v-pagination button:has-text("Previous"), .pagination .previous');
    if (await prevButton.isVisible() && await prevButton.isEnabled()) {
      await prevButton.click();
      await this.waitForLoading();
    }
  }

  async getVisibleQuestions() {
    const questions = this.page.locator('.v-list-item .question-text, .question-item');
    const count = await questions.count();
    const texts = [];
    
    for (let i = 0; i < count; i++) {
      texts.push(await questions.nth(i).textContent());
    }
    
    return texts;
  }

  async hasCategoryPagination() {
    return await this.page.locator('.categories-pagination, .category-list .v-pagination').isVisible();
  }

  async goToNextCategoryPage() {
    const nextButton = this.page.locator('.categories-pagination button:has-text("Next")');
    if (await nextButton.isVisible() && await nextButton.isEnabled()) {
      await nextButton.click();
      await this.waitForLoading();
    }
  }

  async hasUndoOption() {
    return await this.page.locator('button:has-text("Undo"), .undo-button').isVisible({ timeout: 3000 });
  }

  async clickUndo() {
    const undoButton = this.page.locator('button:has-text("Undo"), .undo-button');
    if (await undoButton.isVisible()) {
      await undoButton.click();
      await this.waitForLoading();
    }
  }

  // Error and validation methods
  async hasEmptyState() {
    return await this.emptyState.isVisible();
  }

  async getErrorMessage() {
    const errorAlert = this.page.locator('.v-alert--type-error');
    if (await errorAlert.isVisible()) {
      return await errorAlert.textContent();
    }
    return null;
  }

  async hasValidationErrors() {
    const errorElements = this.page.locator('.v-messages__message, .error--text, [class*="error"]');
    return (await errorElements.count()) > 0;
  }

  // Extended category management methods
  async editFirstCategory() {
    const firstCategory = this.categoryAccordion.locator('.v-expansion-panel').first();
    const editButton = firstCategory.locator('button:has([class*="edit"]), [data-testid="edit-category"]');
    if (await editButton.isVisible()) {
      await editButton.click();
      await this.waitForDialog();
    }
  }

  async selectMultipleCategories(count) {
    const categoryPanels = this.categoryAccordion.locator('.v-expansion-panel');
    const totalCategories = await categoryPanels.count();
    const selectCount = Math.min(count, totalCategories);
    
    for (let i = 0; i < selectCount; i++) {
      const checkbox = categoryPanels.nth(i).locator('.v-checkbox input');
      if (await checkbox.isVisible()) {
        await checkbox.check();
      }
    }
  }

  async performBulkDeleteWithStrategy(strategy, targetCategoryId = null) {
    if (await this.bulkDeleteButton.isVisible()) {
      await this.bulkDeleteButton.click();
      await this.waitForDialog();
      
      // Select strategy in dialog
      const strategySelect = this.deleteConfirmDialog.locator('.v-select, select');
      if (await strategySelect.isVisible()) {
        await strategySelect.click();
        await this.page.locator(`.v-list-item:has-text("${strategy}")`).click();
      }
      
      if (strategy === 'move' && targetCategoryId) {
        const targetSelect = this.deleteConfirmDialog.locator('.target-category-select');
        if (await targetSelect.isVisible()) {
          await targetSelect.click();
          await this.page.locator(`[value="${targetCategoryId}"]`).click();
        }
      }
      
      const confirmButton = this.deleteConfirmDialog.locator('button:has-text("Delete"), button:has-text("Confirm")');
      await confirmButton.click();
      await this.waitForLoading();
      return await this.waitForToast();
    }
  }

  async isDeleteConfirmationVisible() {
    return await this.deleteConfirmDialog.isVisible();
  }

  async confirmBulkDelete() {
    const confirmButton = this.deleteConfirmDialog.locator('button:has-text("Delete"), button:has-text("Confirm")');
    await confirmButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
    await this.waitForLoading();
    return await this.waitForToast();
  }

  async cancelBulkDelete() {
    const cancelButton = this.deleteConfirmDialog.locator('button:has-text("Cancel")');
    await cancelButton.click();
    await this.page.waitForSelector('.v-dialog', { state: 'hidden' });
  }

  async hasSelectAllOption() {
    return await this.page.locator('button:has-text("Select All"), [data-testid="select-all"]').isVisible();
  }

  async selectAllCategories() {
    const selectAllButton = this.page.locator('button:has-text("Select All"), [data-testid="select-all"]');
    if (await selectAllButton.isVisible()) {
      await selectAllButton.click();
    }
  }

  async deselectAllCategories() {
    const deselectAllButton = this.page.locator('button:has-text("Deselect All"), [data-testid="deselect-all"]');
    if (await deselectAllButton.isVisible()) {
      await deselectAllButton.click();
    }
  }

  async areBulkActionsVisible() {
    return await this.bulkActionsCard.isVisible();
  }

  // Performance methods
  async measureSettingsLoad() {
    const startTime = Date.now();
    await this.goto();
    return Date.now() - startTime;
  }
}

export default FollowupSettingsPage;