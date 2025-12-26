package com.arthurassistant.lockout

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

class LockoutManager {
    enum class Category {
        EXTERNAL_TRANSMISSION,
        SCREEN_ACCESS,
        AUTH_ADMIN
    }

    private val lockedCategories = MutableStateFlow(setOf<Category>())
    val locked: StateFlow<Set<Category>> = lockedCategories

    fun enable(category: Category) {
        lockedCategories.value = lockedCategories.value + category
    }

    fun disable(category: Category) {
        lockedCategories.value = lockedCategories.value - category
    }

    fun clearAll() {
        lockedCategories.value = emptySet()
    }

    fun isLocked(category: Category): Boolean = lockedCategories.value.contains(category)
}
