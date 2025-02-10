#!/usr/bin/env python3

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import os
from firebase_interface import get_all_videos, get_transcript
from claim_extractor import extract_claims

console = Console()

def process_video(video_id: str, transcript_text: str) -> list:
    """Process a single video and extract claims."""
    claims = extract_claims(transcript_text)
    return claims

@click.group()
def cli():
    """DeepScope CLI - Test and analyze claim extraction"""
    pass

@cli.command()
@click.option('--limit', default=None, type=int, help='Limit the number of videos to process')
@click.option('--debug/--no-debug', default=True, help='Enable/disable debug output')
def test_claims(limit, debug):
    """Fetch videos from Firebase and test claim extraction"""
    try:
        # Debug Firebase setup
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if debug:
            console.print(f"[blue]Firebase credentials path: {cred_path}[/blue]")

        # Get videos from Firebase
        console.print("[blue]Fetching videos from Firebase...[/blue]")
        videos = get_all_videos()
        
        if debug:
            console.print(f"[blue]Found {len(videos)} videos[/blue]")
            for idx, video in enumerate(videos[:3]):  # Show first 3 videos for debugging
                console.print(f"[dim]Video {idx + 1}:[/dim]")
                for key, value in video.items():
                    if key == 'transcript':
                        console.print(f"[dim]  {key}: <transcript text length: {len(str(value))}>[/dim]")
                    else:
                        console.print(f"[dim]  {key}: {value}[/dim]")

        if not videos:
            console.print("[red]No videos found in Firebase[/red]")
            return

        if limit:
            videos = videos[:limit]
            if debug:
                console.print(f"[blue]Limited to {limit} videos[/blue]")

        # Create a table for output with full width columns
        table = Table(title="Extracted Claims Analysis", show_lines=True)
        table.add_column("Video ID", style="cyan", no_wrap=True)
        table.add_column("Original Text", style="green", max_width=None, overflow="fold")
        table.add_column("Extracted Claims", style="yellow", max_width=None, overflow="fold")

        # Process each video
        for video in videos:
            video_id = video.get('video_id')
            if not video_id:
                if debug:
                    console.print("[red]Video found but missing video_id. Full video data:[/red]")
                    console.print(video)
                continue

            if debug:
                console.print(f"\n[blue]Processing video: {video_id}[/blue]")

            # Try to get transcript directly from video data first
            transcript_text = video.get('transcript', '')
            if not transcript_text:
                if debug:
                    console.print(f"[yellow]No transcript in video data, fetching from get_transcript...[/yellow]")
                transcript = get_transcript(video_id)
                if transcript and transcript.get('text'):
                    transcript_text = transcript['text']
                else:
                    if debug:
                        console.print(f"[red]No transcript found for video {video_id} via get_transcript[/red]")
                    continue
            
            if debug:
                console.print(f"[green]Found transcript of length: {len(transcript_text)}[/green]")

            # Extract claims
            claims = process_video(video_id, transcript_text)
            if debug:
                console.print(f"[green]Extracted {len(claims)} claims[/green]")

            # Add to table (no truncation)
            table.add_row(
                video_id,
                transcript_text,
                "\n".join(claims) if claims else "[red]No claims found[/red]"
            )

        # Print the results
        console.print("\n[bold]Final Results:[/bold]")
        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == '__main__':
    cli() 