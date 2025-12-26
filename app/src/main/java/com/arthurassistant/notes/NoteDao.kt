package com.arthurassistant.notes

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface NoteDao {
    @Insert
    suspend fun insert(note: NoteEntity): Long

    @Query("SELECT * FROM notes ORDER BY createdAtMs DESC LIMIT :limit")
    fun listRecent(limit: Int): Flow<List<NoteEntity>>

    @Query("SELECT * FROM notes WHERE text LIKE :query ORDER BY createdAtMs DESC")
    suspend fun search(query: String): List<NoteEntity>

    @Query("DELETE FROM notes WHERE id = :id")
    suspend fun deleteById(id: Long)
}
