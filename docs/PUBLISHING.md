# Publishing Video Downloader on GitHub (no command line)

About 20 minutes the first time. After that, a release is one click.

## 0. Privacy first (2 min, do this BEFORE publishing)
A public repository shows the **name and email on every commit**, forever.
1. github.com → your photo → **Settings → Emails** → tick **Keep my email addresses private**
   and **Block command line pushes that expose my email**.
2. **Settings → Public profile → Name**: set it to `AKA` (or leave it empty).
3. In GitHub Desktop (step 1): **File → Options → Git** → Name: `AKA`, Email: the
   `…@users.noreply.github.com` address shown on the Emails page.

## 1. Install GitHub Desktop
Download from https://desktop.github.com and sign in with your GitHub account.

## 2. Put the project on your PC
Extract `VideoDownloader-Repo.zip` to `Documents\GitHub\video-downloader`.
You'll see `Setup.bat`, `app`, `build_tools`, `docs`, plus `.github` and `.gitignore`.
Git needs those two at the top. Leave them there.

## 3. Create the repository
1. GitHub Desktop → **File → Add local repository** → choose that folder.
2. It says "This directory does not appear to be a Git repository" → click
   **create a repository**. Name: `video-downloader`. Git ignore: **None**, License: **None**
   (both are already included) → **Create repository**.
3. Click **Publish repository**. **Untick "Keep this code private"** → **Publish**.

## 4. One-time settings on github.com
Open your repository on github.com:
1. **Settings → Code security → Private vulnerability reporting → Enable**
   (people can report security problems to you privately, without your email).
2. **Actions** tab → if asked, click **I understand my workflows, go ahead and enable them**.

## 5. Release (every time, one click)
1. **Actions** tab → **Build & release** → **Run workflow** → **Run workflow**.
2. Wait about 15 minutes for the green tick. A red X means it stopped on purpose: a scan or
   test failed, so nothing broken was published. Send a screenshot of the failed step.
3. **Releases** (right side of the repo page) now shows `VideoDownloader-Setup-V1.exe`.
   That page is the link you share.

## 6. Making changes later
1. Replace the changed files in the folder.
2. GitHub Desktop: write a short summary → **Commit to main** → **Push origin**.
3. The **Check** workflow runs scans + tests automatically (green tick = OK).
4. Run step 5 to publish.

## Single source of truth
From now on **this GitHub repository is the master copy** of Video Downloader.
The Claude project and old ZIPs are copies. Link the repo from your vault's Builds Hub.
