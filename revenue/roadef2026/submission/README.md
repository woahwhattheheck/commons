# ROADEF/EURO 2026 qualification entry materials

Prepared 7 September 2026 from SEDGE's accepted delivery and the current organizer rules. This directory is submission support, not another solver. The source remains [SEDGE's solver](../sedge/README.md), original commit `c7c8679bb0330c932413e85f8f0646b30501cf07`.

## Registration payload

Use the [official form](https://roadef.org/challenge/2026/en/registration.php) only once, after checking existing correspondence. The root session owns this external action.

| Field | Actual value |
| --- | --- |
| Corresponding member first name | Bryce Xavier |
| Name / surname | Muhlnickel |
| Mail | tokenjunkielabs@gmail.com |
| Institution | Leave blank; optional |
| Country | USA |
| Junior team | Unchecked |
| Additional members | None for the instructed solo entry |

No team name, biography, degree, signature, phone, postal address, or payment-card field appears in the inspected form. The organizer assigns the team ID. Do not use SEDGE or TokenJunkieLabs as an invented human member. No further owner facts are missing for this payload.

Rules permit any team size, with each individual on only one team. Junior requires every member to be a student on 31 December 2026, with no PhD defended before then. Orange employees, Orange interns, and committee members are excluded; the homepage also excludes people professionally involved with industrial partners. No nationality or onsite-attendance restriction or AI-specific prohibition was found in the inspected rules.

## Exact outgoing email, after the real team ID exists

To: challenge.roadef2026@orange.com  
Subject: `[ChallengeROADEF2026] [qualification] <team ID>`  
Attachment: `<team ID>.zip`

> Dear ROADEF/EURO 2026 Organizing Team,
>
> Please find attached the qualification program and two-page method description for team <team ID>.
>
> The archive contains the Dockerfile, four-argument run.sh wrapper, C++20 source, vendored RapidJSON headers and licenses, and method.pdf. The Docker build compiles the executable. No commercial solver or runtime network access is required.
>
> Please confirm receipt and let me know if any packaging or execution issue requires attention.
>
> Best regards,  
> Bryce Xavier Muhlnickel  
> tokenjunkielabs@gmail.com

Replace only `<team ID>` with the organizer-issued identifier; it is not a placeholder to invent. No email is sent by this directory or its workflow. The last email received before the deadline is the evaluated version. Record the sent-message identifier and organizer acknowledgement. If necessary, a transfer link is expressly allowed for an archive too large to email.

## Deadline and execution contract

Qualification: **14 September 2026, 23:59 French local time = 21:59 UTC = 17:59 EDT**. The official rules require registration before submission but state no separate registration cutoff. The earlier card's September 12 date remains a conservative action target, not a separately verified organizer cutoff.

The evaluated deliverable is an executable program, not a bundle of public-set solutions. Hidden set X determines qualification; the completed 12/12 set-B validation remains accepted public-instance evidence. Qualification also considers documentation quality.

- ZIP contains Dockerfile, run.sh, implementation files and a method document of at most two pages.
- Compiling C++ inside Docker is explicitly demonstrated by Appendix A; a precompiled native binary is not required.
- Build: internet available, at most 4 GB RAM and 30 minutes.
- Evaluation: Ubuntu 24.04, 8 CPUs (Xeon 2.80 GHz), 32 GB RAM, one run per hidden instance.
- run.sh receives topology, traffic matrix, intervention scenario and output-solution path, in that order.
- Qualification limit: 600 seconds. SIGTERM at 590 seconds; graceful exit within 10 seconds, then SIGKILL. A missing output earns no points.
- No runtime networking except the organizer's specified solver-license exception; this candidate needs none.
- SEDGE's default 565-second allowance, exec wrapper and atomic output preservation are unchanged.
- Participants retain program IP; reports may be used by Orange. Participation is not a partnership or contract.

## Cloud packaging

The original source ZIP has a containing `sedge-roadef-solver/` directory. This is not identified as a solver defect. `package.py` makes the build context convenient by placing its contents at the archive root and replacing only README, method PDF, method-generation source and container receipt with the current published documentation. Every solver, build, wrapper, vendor and license byte is compared against the original delivered archive.

Run the **ROADEF entry package** GitHub Actions workflow in the ephemeral Ubuntu runner; pass the real team ID if available. Its artifact contains the ZIP and a complete SHA-256 manifest. Do not create a new local Commons build tree or archive on the owner's machine. The script does not build, tune, register, send mail, or submit anything.

Without an ID the archive is clearly named `qualification-unregistered.zip`; after registration it must be named exactly `<team ID>.zip`. Renaming changes no ZIP bytes. Do not attach the outer GitHub Actions artifact ZIP; attach the inner qualification ZIP.

## Source coverage and accepted evidence

Read: current organizer homepage, schedule, registration form fields, all 13 pages of the rules PDF; SEDGE README, C++ source, run.sh, Dockerfile, Makefile, method generator, two-page PDF visually, archive member inventory, and container receipt. The source ZIP preserves its original delivery hash. Third-party header internals and full retained checker logs were not re-audited; this task does not reopen accepted algorithm results.

- [Organizer rules, sections 1, 2.4, 2.6-2.9, 4 and Appendices A-B](https://gitlab.com/Orange-OpenSource/network-optimization-tools/challenge-roadef-2026/-/blob/d84d319a7fdb8de3b1866830d2eaa2937871e5ae/doc/Challenge_Orange_ROADEF_2026_Rules.pdf)
- [Official schedule](https://roadef.org/challenge/2026/en/calendrier.php)
- [Eligibility](https://roadef.org/challenge/2026/en/)
- [Original thread and handoff](https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788750090535979)
- [Accepted Docker run 34080604676](https://github.com/woahwhattheheck/commons/actions/runs/34080604676)
- [Accepted native and container evidence](../sedge/README.md)

No independent optimizer order is duplicated here: the root already posted that separate lane in #delegations.
