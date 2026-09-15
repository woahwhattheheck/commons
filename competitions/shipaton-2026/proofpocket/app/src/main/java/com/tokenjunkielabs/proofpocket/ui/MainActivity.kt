package com.tokenjunkielabs.proofpocket.ui

import android.app.Activity
import android.content.Intent
import android.database.Cursor
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.View
import android.widget.*
import com.tokenjunkielabs.proofpocket.billing.BillingState
import com.tokenjunkielabs.proofpocket.billing.RevenueCatGate
import com.tokenjunkielabs.proofpocket.core.Evidence
import com.tokenjunkielabs.proofpocket.core.Receipt
import com.tokenjunkielabs.proofpocket.core.ReceiptCodec
import com.tokenjunkielabs.proofpocket.core.ReceiptEngine
import com.tokenjunkielabs.proofpocket.core.ReceiptImportLimits
import com.tokenjunkielabs.proofpocket.export.PdfExporter
import com.tokenjunkielabs.proofpocket.store.ProjectDraft
import com.tokenjunkielabs.proofpocket.store.ProofRepository
import java.security.MessageDigest
import java.time.Instant

class MainActivity : Activity() {
    companion object {
        private const val PICK_EVIDENCE = 41
        private const val EXPORT_JSON = 42
        private const val EXPORT_PDF = 43
        private const val IMPORT_RECEIPT = 44
        private const val FREE_PROJECT_LIMIT = 3
    }

    private lateinit var repo: ProofRepository
    private lateinit var billing: RevenueCatGate
    private val projects = mutableListOf<ProjectDraft>()
    private var selected = 0
    private var pendingReceipt: Receipt? = null

    private lateinit var projectSpinner: Spinner
    private lateinit var titleInput: EditText
    private lateinit var claimInput: EditText
    private lateinit var evidenceView: TextView
    private lateinit var billingView: TextView
    private lateinit var statusView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repo = ProofRepository(this)
        projects += repo.load()
        billing = RevenueCatGate(this)
        setContentView(buildUi())
        if (projects.isEmpty()) addProject("First proof project") else renderProject(0)
        billing.configure(::renderBilling)
    }

    private fun buildUi(): View {
        val scroll = ScrollView(this)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 28, 32, 48)
        }
        scroll.addView(root)
        root.addView(TextView(this).apply { text = "ProofPocket"; textSize = 28f })
        root.addView(TextView(this).apply { text = "Local, content-addressed work receipts. Evidence files never leave the device through ProofPocket." })

        projectSpinner = Spinner(this).also { spinner ->
            spinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
                override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: View?, position: Int, id: Long) {
                    if (position in projects.indices) { saveCurrent(); renderProject(position) }
                }
            }
            root.addView(spinner)
        }
        root.addView(Button(this).apply { text = "New project"; setOnClickListener { createProjectTapped() } })
        titleInput = EditText(this).apply { hint = "Project title" }.also(root::addView)
        claimInput = EditText(this).apply { hint = "Bounded completion claim"; minLines = 3 }.also(root::addView)
        root.addView(Button(this).apply { text = "Attach local evidence"; setOnClickListener { pickEvidence() } })
        evidenceView = TextView(this).also(root::addView)
        root.addView(Button(this).apply { text = "Create / verify receipt"; setOnClickListener { createReceipt() } })
        root.addView(Button(this).apply { text = "Export JSON receipt"; setOnClickListener { exportJson() } })
        root.addView(Button(this).apply { text = "Import + verify receipt"; setOnClickListener { importReceipt() } })
        root.addView(Button(this).apply { text = "Export Pro PDF proof pack"; setOnClickListener { exportPdf() } })

        billingView = TextView(this).also(root::addView)
        root.addView(Button(this).apply { text = "Unlock Pro"; setOnClickListener { billing.purchaseCurrent(this@MainActivity, ::renderBilling) } })
        root.addView(Button(this).apply { text = "Restore purchases"; setOnClickListener { billing.restore(::renderBilling) } })
        statusView = TextView(this).apply { setPadding(0, 24, 0, 0) }.also(root::addView)
        return scroll
    }

    private fun createProjectTapped() {
        saveCurrent()
        if (!billing.isPro() && projects.size >= FREE_PROJECT_LIMIT) {
            status("Free tier allows $FREE_PROJECT_LIMIT projects. RevenueCat Pro entitlement is required for more.")
            return
        }
        addProject("Project ${projects.size + 1}")
    }

    private fun addProject(title: String) {
        projects += repo.newProject(title)
        repo.save(projects)
        refreshSpinner(projects.lastIndex)
    }

    private fun refreshSpinner(select: Int = selected) {
        projectSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, projects.map { it.title })
        selected = select.coerceIn(0, projects.lastIndex.coerceAtLeast(0))
        if (projects.isNotEmpty()) projectSpinner.setSelection(selected)
        if (projects.isNotEmpty()) renderProject(selected)
    }

    private fun renderProject(index: Int) {
        selected = index
        val p = projects[index]
        titleInput.setText(p.title)
        claimInput.setText(p.claim)
        evidenceView.text = if (p.evidence.isEmpty()) "No evidence attached" else p.evidence.joinToString("\n") {
            "• ${it.name} · ${it.sizeBytes} B · ${it.sha256.take(16)}…"
        }
    }

    private fun saveCurrent() {
        if (projects.isEmpty() || selected !in projects.indices || !::titleInput.isInitialized) return
        projects[selected].title = titleInput.text.toString().trim().ifBlank { projects[selected].title }
        projects[selected].claim = claimInput.text.toString().trim()
        repo.save(projects)
    }

    private fun pickEvidence() {
        saveCurrent()
        startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply { type = "*/*"; addCategory(Intent.CATEGORY_OPENABLE) }, PICK_EVIDENCE)
    }

    private fun createReceipt(): Receipt? {
        saveCurrent()
        if (selected !in projects.indices) return null
        val p = projects[selected]
        return try {
            ReceiptEngine.issue(p.id, p.title, p.claim, Instant.now().toString(), p.evidence).also {
                pendingReceipt = it
                status("Receipt valid: ${it.receiptId}")
            }
        } catch (e: IllegalArgumentException) {
            status("Cannot issue receipt: ${e.message}")
            null
        }
    }

    private fun exportJson() {
        val receipt = createReceipt() ?: return
        pendingReceipt = receipt
        startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            type = "application/json"; putExtra(Intent.EXTRA_TITLE, "proofpocket-${receipt.receiptId.take(12)}.json")
        }, EXPORT_JSON)
    }

    private fun exportPdf() {
        if (!billing.isPro()) { status("PDF proof packs require an observed active RevenueCat Pro entitlement."); return }
        val receipt = createReceipt() ?: return
        pendingReceipt = receipt
        startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            type = "application/pdf"; putExtra(Intent.EXTRA_TITLE, "proofpocket-${receipt.receiptId.take(12)}.pdf")
        }, EXPORT_PDF)
    }

    private fun importReceipt() {
        startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply { type = "application/json"; addCategory(Intent.CATEGORY_OPENABLE) }, IMPORT_RECEIPT)
    }

    @Deprecated("Legacy callback keeps this carrier dependency-light and API-26 compatible")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK || data?.data == null) return
        val uri = data.data!!
        when (requestCode) {
            PICK_EVIDENCE -> attachEvidence(uri)
            EXPORT_JSON -> pendingReceipt?.let { receipt -> contentResolver.openOutputStream(uri)?.use { it.write(ReceiptEngine.exportJson(receipt).toByteArray()) }; status("JSON receipt exported") }
            EXPORT_PDF -> pendingReceipt?.let { receipt -> contentResolver.openOutputStream(uri)?.use { PdfExporter.write(receipt, it) }; status("PDF proof pack exported") }
            IMPORT_RECEIPT -> try {
                val input = contentResolver.openInputStream(uri)
                    ?: throw IllegalArgumentException("unable to read selected receipt")
                val raw = input.use(ReceiptImportLimits::readUtf8Bounded)
                val (_, verification) = ReceiptCodec.decodeAndVerify(raw)
                status(if (verification.valid) "Imported receipt verified" else "Imported receipt rejected: ${verification.reason}")
            } catch (e: Exception) {
                status("Imported receipt rejected: ${e.message ?: "invalid or unreadable receipt"}")
            }
        }
    }

    private fun attachEvidence(uri: Uri) {
        if (selected !in projects.indices) return
        try {
            val digest = MessageDigest.getInstance("SHA-256")
            contentResolver.openInputStream(uri)?.use { input ->
                val buf = ByteArray(64 * 1024)
                while (true) { val n = input.read(buf); if (n <= 0) break; digest.update(buf, 0, n) }
            } ?: error("unable to read selected content")
            val sha = digest.digest().joinToString("") { "%02x".format(it) }
            val (name, size) = queryNameSize(uri)
            val evidence = Evidence(ReceiptEngine.evidenceId(sha), name, contentResolver.getType(uri) ?: "application/octet-stream", sha, size)
            if (projects[selected].evidence.any { it.id == evidence.id }) { status("That exact evidence content is already attached"); return }
            projects[selected].evidence += evidence
            repo.save(projects)
            renderProject(selected)
            status("Evidence hashed locally and attached")
        } catch (e: Exception) {
            status("Evidence attach failed: ${e.message}")
        }
    }

    private fun queryNameSize(uri: Uri): Pair<String, Long> {
        var name = "evidence"
        var size = 0L
        val cursor: Cursor? = contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)
        cursor?.use {
            if (it.moveToFirst()) {
                val nameIndex = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                val sizeIndex = it.getColumnIndex(OpenableColumns.SIZE)
                if (nameIndex >= 0) name = it.getString(nameIndex) ?: name
                if (sizeIndex >= 0 && !it.isNull(sizeIndex)) size = it.getLong(sizeIndex)
            }
        }
        return name to size
    }

    private fun renderBilling(state: BillingState) {
        runOnUiThread {
            billingView.text = when (state) {
                BillingState.NotConfigured -> "RevenueCat: not configured — public SDK key required; Pro remains locked"
                BillingState.Loading -> "RevenueCat: checking entitlement…"
                is BillingState.Ready -> "RevenueCat: ${if (state.pro) "Pro active" else "Free"} — ${state.message}"
                is BillingState.Error -> "RevenueCat: ${state.message}; Pro remains locked"
            }
        }
    }

    private fun status(message: String) { statusView.text = message }

    override fun onStop() { saveCurrent(); super.onStop() }
}
