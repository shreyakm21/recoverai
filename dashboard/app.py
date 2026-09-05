import streamlit as st
import requests
import pandas as pd

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="RecoverAI Dashboard",
    layout="wide"
)

st.title("RecoverAI")
st.caption("Intelligent Failed Payment Recovery Dashboard")


def get_json(endpoint):
    response = requests.get(f"{API_BASE}{endpoint}", timeout=10)
    response.raise_for_status()
    return response.json()


try:
    # --------------------------------------------------
    # Header Actions
    # --------------------------------------------------

    header_col1, header_col2 = st.columns([6, 1])

    with header_col1:
        st.markdown(
            "**Live recovery monitoring with policy-controlled actions "
            "and Razorpay Test Mode integration.**"
        )

    with header_col2:
        if st.button("Refresh Dashboard"):
            st.rerun()

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    summary = get_json("/recovery/summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Initial Revenue at Risk",
        f"₹{summary['initial_revenue_at_risk']:,}"
    )

    col2.metric(
        "Revenue Recovered",
        f"₹{summary['revenue_recovered']:,}"
    )

    col3.metric(
        "Recovery Rate",
        f"{summary['recovery_rate_percent']}%"
    )

    col4.metric(
        "Remaining Failed",
        summary["remaining_failed_payments"]
    )

    st.divider()

    # --------------------------------------------------
    # Recovery Progress
    # --------------------------------------------------

    st.subheader("Recovery Progress")

    recovery_rate = summary["recovery_rate_percent"] / 100

    st.progress(
        min(max(recovery_rate, 0.0), 1.0),
        text=(
            f"{summary['recovery_rate_percent']}% of initial "
            f"revenue at risk recovered"
        )
    )

    st.caption(
        f"₹{summary['revenue_recovered']:,} recovered from "
        f"₹{summary['initial_revenue_at_risk']:,} initially at risk."
    )

    st.divider()

    # --------------------------------------------------
    # Recovery Status
    # --------------------------------------------------

    st.subheader("Recovery Status")

    col5, col6, col7 = st.columns(3)

    col5.metric(
        "Recovered Payments",
        summary["recovered_payments"]
    )

    col6.metric(
        "Blocked Payments",
        summary["blocked_payments"]
    )

    col7.metric(
        "Remaining Revenue at Risk",
        f"₹{summary['remaining_revenue_at_risk']:,}"
    )

    st.divider()

    # --------------------------------------------------
    # Failed Payments
    # --------------------------------------------------

    st.subheader("Failed Payments")

    failed_response = get_json("/payments/failed")
    failed_payments = failed_response["payments"]

    if failed_payments:
        df = pd.DataFrame(failed_payments)

        display_columns = [
            "payment_id",
            "amount",
            "payment_method",
            "failure_code",
            "retry_count",
            "recovery_status"
        ]

        available_columns = [
            col for col in display_columns
            if col in df.columns
        ]

        st.dataframe(
            df[available_columns],
            width="stretch",
            hide_index=True
        )

        # --------------------------------------------------
        # Failure Distribution
        # --------------------------------------------------

        st.subheader("Failure Distribution")

        failure_counts = (
            df["failure_code"]
            .value_counts()
            .rename_axis("failure_code")
            .reset_index(name="count")
        )

        st.bar_chart(
            failure_counts,
            x="failure_code",
            y="count"
        )

    else:
        st.success("No failed payments remaining.")

    st.divider()

    # --------------------------------------------------
    # Recovery Agent
    # --------------------------------------------------

    st.subheader("Recovery Agent")

    if failed_payments:

        payment_ids = [
            payment["payment_id"]
            for payment in failed_payments
        ]

        selected_payment_id = st.selectbox(
            "Select a failed payment",
            payment_ids
        )

        selected_payment = next(
            payment
            for payment in failed_payments
            if payment["payment_id"] == selected_payment_id
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Amount",
            f"₹{selected_payment['amount']:,}"
        )

        col2.metric(
            "Failure",
            selected_payment["failure_code"]
        )

        col3.metric(
            "Retry Count",
            selected_payment["retry_count"]
        )

        # --------------------------------------------------
        # Recovery Recommendation
        # --------------------------------------------------

        try:
            advice = get_json(
                f"/recovery/advice/{selected_payment_id}"
            )

            st.subheader("Recovery Recommendation")

            recommendation = advice["ai_advice"]
            policy = advice["policy_decision"]

            risk_level = recommendation["risk_level"]

            if risk_level == "LOW":
                st.success("Risk Level: LOW")
            elif risk_level == "MEDIUM":
                st.warning("Risk Level: MEDIUM")
            else:
                st.error("Risk Level: HIGH")

            col4, col5 = st.columns(2)

            with col4:
                st.markdown("### Recovery Advisor")

                st.write(
                    f"**Diagnosis:** "
                    f"{recommendation['diagnosis']}"
                )

                st.write(
                    f"**Recommended Action:** "
                    f"{recommendation['recommended_action']}"
                )

                st.write(
                    f"**Reasoning:** "
                    f"{recommendation['reasoning']}"
                )

            with col5:
                st.markdown("### Policy Engine")

                st.write(
                    f"**Action:** {policy['action']}"
                )

                st.write(
                    f"**Reason:** {policy['reason']}"
                )

                if policy["allowed"]:
                    st.success(
                        "Automatic action allowed by policy."
                    )
                else:
                    st.error(
                        "Automatic action blocked by policy."
                    )

                if advice["recommendation_matches_policy"]:
                    st.info(
                        "Advisor recommendation matches policy."
                    )
                else:
                    st.warning(
                        "Advisor recommendation differs from policy."
                    )

            # --------------------------------------------------
            # Execute Recovery
            # --------------------------------------------------

            st.divider()

            st.subheader("Execute Recovery")

            if policy["allowed"]:

                if st.button(
                    "Process Recovery",
                    type="primary"
                ):
                    try:
                        response = requests.post(
                            f"{API_BASE}/recovery/process/"
                            f"{selected_payment_id}",
                            timeout=10
                        )

                        result = response.json()

                        if response.ok:
                            recovery_result = result[
                                "recovery_result"
                            ]

                            if recovery_result == "RECOVERED":
                                st.success(
                                    "Recovery processed successfully."
                                )

                            elif recovery_result == "FAILED":
                                st.error(
                                    "Recovery attempt failed."
                                )

                            elif recovery_result == "BLOCKED":
                                st.warning(
                                    "Recovery action was blocked."
                                )

                            else:
                                st.info(
                                    f"Recovery result: "
                                    f"{recovery_result}"
                                )

                            st.json(result)

                            st.info(
                                "Click Refresh Dashboard to load "
                                "the latest metrics and audit history."
                            )

                        else:
                            st.error(result)

                    except Exception as error:
                        st.error(
                            f"Recovery request failed: {error}"
                        )

            else:
                st.warning(
                    "Automatic recovery blocked by policy. "
                    "Manual customer action or review is required."
                )

        except Exception as error:
            st.warning(
                f"Unable to load recovery advice: {error}"
            )

        # --------------------------------------------------
        # Recovery Audit Timeline
        # --------------------------------------------------

        st.divider()

        st.subheader("Recovery Audit Timeline")

        try:
            audit = get_json(
                f"/recovery/audit/{selected_payment_id}"
            )

            audit_col1, audit_col2 = st.columns(2)

            audit_col1.metric(
                "Total Recovery Attempts",
                audit["attempt_count"]
            )

            audit_col2.metric(
                "Current Status",
                audit["payment"]["recovery_status"].upper()
            )

            timeline = audit["timeline"]

            if timeline:
                audit_df = pd.DataFrame(timeline)

                if "processed_at" in audit_df.columns:
                    audit_df["processed_at"] = pd.to_datetime(
                        audit_df["processed_at"],
                        errors="coerce"
                    )

                    audit_df["processed_at"] = (
                        audit_df["processed_at"]
                        .dt.strftime("%Y-%m-%d %H:%M:%S")
                    )

                audit_df = audit_df.rename(
                    columns={
                        "recommended_action": "Action",
                        "action_allowed": "Allowed",
                        "decision_reason": "Decision Reason",
                        "recovery_result": "Result",
                        "recovered_amount": "Recovered Amount",
                        "processed_at": "Processed At"
                    }
                )

                preferred_columns = [
                    "Action",
                    "Allowed",
                    "Decision Reason",
                    "Result",
                    "Recovered Amount",
                    "Processed At"
                ]

                available_audit_columns = [
                    col for col in preferred_columns
                    if col in audit_df.columns
                ]

                st.dataframe(
                    audit_df[available_audit_columns],
                    width="stretch",
                    hide_index=True
                )

            else:
                st.info(
                    "No recovery attempts recorded yet."
                )

        except Exception as error:
            st.warning(
                f"Unable to load recovery audit: {error}"
            )

    else:
        st.info(
            "There are no failed payments available for recovery."
        )

    # --------------------------------------------------
    # System Status
    # --------------------------------------------------

    st.divider()

    st.subheader("System Status")

    status_col1, status_col2, status_col3 = st.columns(3)

    status_col1.success(
        "FastAPI Backend Connected"
    )

    status_col2.success(
        "Policy Engine Active"
    )

    status_col3.info(
        "Razorpay Test Mode Integrated"
    )


except requests.exceptions.ConnectionError:
    st.error(
        "RecoverAI backend is not running. "
        "Start FastAPI on port 8000."
    )

except Exception as error:
    st.error(
        f"Error loading dashboard: {error}"
    )