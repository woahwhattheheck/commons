import com.tokenjunkielabs.proofpocket.core.StrictJsonKeys

private fun expectStrictFailure(raw: String) {
    var failed = false
    try { StrictJsonKeys.requireNoDuplicateObjectKeys(raw) } catch (_: IllegalArgumentException) { failed = true }
    check(failed) { "expected strict JSON failure: $raw" }
}

fun main() {
    StrictJsonKeys.requireNoDuplicateObjectKeys("{\"a\":1,\"b\":{\"x\":2},\"c\":[{\"z\":3},{\"z\":4}]}")
    expectStrictFailure("{\"a\":1,\"a\":2}")
    expectStrictFailure("{\"a\":{\"x\":1,\"x\":2}}")
    expectStrictFailure("{\"id\":1,\"\\u0069d\":2}")
    StrictJsonKeys.requireNoDuplicateObjectKeys("[{\"id\":1},{\"id\":2}]")
    println("STRICT_JSON_OK")
}
