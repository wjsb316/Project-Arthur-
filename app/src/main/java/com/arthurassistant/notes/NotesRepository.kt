package com.arthurassistant.notes

import kotlinx.coroutines.flow.Flow

class NotesRepository(private val noteDao: NoteDao) {
    suspend fun createNote(text: String): Long {
        val note = NoteEntity(
            createdAtMs = System.currentTimeMillis(),
            text = text
        )
        return noteDao.insert(note)
    }

    fun recentNotes(limit: Int = 20): Flow<List<NoteEntity>> = noteDao.listRecent(limit)

    suspend fun searchNotes(query: String): List<NoteEntity> = noteDao.search("%$query%")

    suspend fun deleteNote(id: Long) {
        noteDao.deleteById(id)
    }
}
