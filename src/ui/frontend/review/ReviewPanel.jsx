import { useEffect, useState } from "react";
import { getReview, saveRevision, transitionRevision } from "../api/reviews.js";
import { publishRevision } from "../api/publications.js";

export default function ReviewPanel({ api, jobId, onError }) {
  const [review, setReview] = useState(null); const [changes, setChanges] = useState("{}");
  const load = () => getReview(api, jobId).then(setReview).catch((e) => onError(e.message));
  useEffect(() => { load(); }, [jobId]);
  const revisionId = review?.currentRevision?.revisionId || review?.revisions?.at(-1)?.revisionId;
  async function action(name) { try { const result = name === "publish" ? await publishRevision(api, jobId, revisionId) : name === "save" ? await saveRevision(api, jobId, JSON.parse(changes), revisionId) : await transitionRevision(api, jobId, name, revisionId); setReview(result.review || result); } catch (e) { onError(e.status === 409 ? "This review was changed in another session. Refresh before saving again." : e.message); } }
  if (!review) return <section className="card"><p>Loading review…</p></section>;
  return <section className="card review"><h2>Structured review</h2><p>Status: {review.reviewStatus || "machine-unreviewed"}</p><label>Finding changes (structured JSON)<textarea aria-label="Finding changes" value={changes} onChange={(e) => setChanges(e.target.value)} /></label><div className="actions"><button onClick={() => action("save")}>Save revision</button><button onClick={() => action("validate")}>Validate</button><button onClick={() => action("approve")}>Approve</button><button onClick={() => action("publish")}>Publish reviewed report</button></div><h3>Revision history</h3><ul>{(review.revisions || []).map((item) => <li key={item.revisionId}>{item.revisionId} — {item.reviewStatus}</li>)}</ul></section>;
}
